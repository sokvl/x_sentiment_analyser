import time
from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import SimpleTestCase

from scraper.scraper import Scraper
from scraper.scraper import ScraperStates
from scraper.scrapers.twitter_scraper import TwitterScraper


def make_scraper(config=None) -> TwitterScraper:
    # Skip TwitterScraper.__init__ (needs DATA_MANAGER from the app
    # registry); run Scraper.__init__ directly so state/logs/events exist.
    scraper = object.__new__(TwitterScraper)
    Scraper.__init__(scraper, config or {})
    return scraper


def tweet_html(like=None, retweet=None, reply=None, views_aria_label=None) -> str:
    def button(testid, text):
        if text is None:
            return ''
        return f'<button data-testid="{testid}"><span>{text}</span></button>'

    views = ''
    if views_aria_label is not None:
        views = f'<a aria-label="{views_aria_label}">View post analytics</a>'

    return f"""
    <article>
        {button('like', like)}
        {button('retweet', retweet)}
        {button('reply', reply)}
        {views}
    </article>
    """


class ExtractTweetMetadataTests(SimpleTestCase):
    def setUp(self):
        self.scraper = make_scraper()

    def test_plain_counts_are_parsed(self):
        html = tweet_html(like='42', retweet='7', reply='3')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertEqual(result['likes'], 42)
        self.assertEqual(result['retweets'], 7)
        self.assertEqual(result['replies'], 3)

    def test_whole_number_k_abbreviation_parses_by_coincidence(self):
        html = tweet_html(like='12K')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertEqual(result['likes'], 12000)

    def test_decimal_k_abbreviation_silently_returns_none(self):
        html = tweet_html(like='1.2K')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['likes'])

    def test_decimal_m_abbreviation_silently_returns_none(self):
        html = tweet_html(retweet='3.4M')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['retweets'])

    def test_malformed_count_returns_none(self):
        html = tweet_html(reply='not-a-number')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['replies'])

    def test_missing_buttons_return_none(self):
        html = tweet_html()
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['likes'])
        self.assertIsNone(result['retweets'])
        self.assertIsNone(result['replies'])

    def test_views_parsed_from_aria_label(self):
        html = tweet_html(views_aria_label='1,234 views. View post analytics')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertEqual(result['views'], 1234)

    def test_views_missing_returns_none(self):
        html = tweet_html()
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['views'])

    def test_views_aria_label_with_no_digits_returns_none(self):
        html = tweet_html(views_aria_label='no numbers here views')
        result = self.scraper._extract_tweet_metadata(html)
        self.assertIsNone(result['views'])


class MaxTimeRunningExceededTests(SimpleTestCase):
    def test_none_means_unlimited(self):
        scraper = make_scraper({'max_time_running': None})
        scraper._run_started_at = time.time() - 10_000
        self.assertFalse(scraper._max_time_running_exceeded())

    def test_not_yet_exceeded(self):
        scraper = make_scraper({'max_time_running': 3600})
        scraper._run_started_at = time.time()
        self.assertFalse(scraper._max_time_running_exceeded())

    def test_exceeded(self):
        scraper = make_scraper({'max_time_running': 1})
        scraper._run_started_at = time.time() - 10
        self.assertTrue(scraper._max_time_running_exceeded())


def growing_scroll_height(script, *args, **kwargs):
    """Fake `execute_script`: only the 'return ...scrollHeight' calls need a
    return value, and it grows forever so the loop never hits its own
    'no new content' break — only max_time_running should be able to stop it.
    The 'window.scrollTo(...)' calls are fire-and-forget in the real code."""
    if 'scrollHeight' not in script:
        return None
    growing_scroll_height.height += 1000
    return growing_scroll_height.height


class ScrollAndCollectMaxTimeRunningTests(SimpleTestCase):
    def setUp(self):
        growing_scroll_height.height = 0
        self.sleep_patcher = patch('scraper.scrapers.twitter_scraper.time.sleep')
        self.sleep_patcher.start()
        self.addCleanup(self.sleep_patcher.stop)

        self.scraper = make_scraper({'max_time_running': 0})
        # max_time_running=0 with a start time in the past means the very
        # first loop check already reports exceeded.
        self.scraper._run_started_at = time.time() - 10

        self.scraper.instance = MagicMock()
        self.scraper.instance.execute_script.side_effect = growing_scroll_height
        self.scraper.instance.page_source = '<html></html>'

    def test_stops_immediately_when_max_time_running_exceeded(self):
        count = self.scraper._scroll_and_collect('$AAPL')

        self.assertEqual(count, 0)
        self.assertTrue(self.scraper.stop_event.is_set())
        self.assertEqual(self.scraper.state, ScraperStates.STOPPED)

    def test_does_not_stop_when_time_budget_remains(self):
        self.scraper.config['max_time_running'] = 3600
        self.scraper._run_started_at = time.time()

        # Simulate an external stop request (e.g. the user clicking "stop")
        # arriving after a few scroll iterations, so the loop terminates
        # deterministically without ever exhausting the time budget.
        calls = {'n': 0}

        def side_effect(script, *args, **kwargs):
            if 'scrollHeight' not in script:
                return None
            calls['n'] += 1
            if calls['n'] >= 3:
                self.scraper.stop_event.set()
            return calls['n'] * 1000

        self.scraper.instance.execute_script.side_effect = side_effect

        self.scraper._scroll_and_collect('$AAPL')

        # state stayed IDLE (never transitioned to STOPPED via self.stop()),
        # proving _max_time_running_exceeded never fired here.
        self.assertEqual(self.scraper.state, ScraperStates.IDLE)
