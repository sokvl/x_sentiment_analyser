from __future__ import annotations

import logging
import os
import queue
import time
from datetime import datetime
from datetime import timedelta
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from stocknlp.tasks import enqueue_scraper_data

from ..scraper import LogTypes
from ..scraper import Scraper
from ..scraper import ScraperStates
# import chromedriver_autoinstaller
### DB RELATED IMPORTS ###
### INTERNAL IMPORTS ###

load_dotenv()

logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)


class TwitterScraper(Scraper):

    # Fallback defaults — used when no active Config exists in the DB.
    _DEFAULT_CONFIG = {
        'crawl_interval': 60,
        'source': [{'name': 'twitter', 'base_url': 'https://x.com/search?q='}],
        'max_time_running': None,
        'threads': 1,
        'twitter_query': {
            'params': {
                'filter': ['links', 'replies', 'media&src=typed_query'],
                'lang': 'en',
                'keywords': ['stock', 'market', 'trading', 'investing', 'shares'],
                'ticker': ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOG'],
            },
        },
    }

    def __init__(self):
        self.data_manager = apps.get_app_config('scraper').DATA_MANAGER
        # Bootstrap with defaults — load_config() overwrites this from DB before run.
        super().__init__(self._build_fallback_config())

    @staticmethod
    def _get_credentials() -> dict:
        """Credentials always come from env vars — never from DB."""
        return {
            'email': os.getenv('TWITTER_EMAIL'),
            'username': os.getenv('TWITTER_USERNAME'),
            'password': os.getenv('TWITTER_PASSWORD'),
        }

    @classmethod
    def _build_fallback_config(cls) -> dict:
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        defaults = cls._DEFAULT_CONFIG
        return {
            'crawl_interval': defaults['crawl_interval'],
            'source': defaults['source'],
            'credentials': cls._get_credentials(),
            'max_time_running': defaults['max_time_running'],
            'threads': defaults['threads'],
            'twitter_query': {
                'start_date': yesterday,
                'end_date': today,
                'params': dict(defaults['twitter_query']['params']),
            },
        }

    def load_config(self) -> None:
        """
        Load configuration from the active Config record in the DB.
        Falls back to hardcoded defaults if no active Config exists.
        Credentials always come from env vars regardless of source.
        """
        fallback = self._build_fallback_config()
        try:
            config_obj = apps.get_app_config('scraper').get_model(
                'Config',
            ).objects.get(active=True)
            config_string = config_obj.config_string
            user_config = config_string['user_config']
            scrapers_config = config_string['scrapers_config'][0]

            tq = scrapers_config.get('twitter_query', {})
            tq_params = tq.get('params', {})
            fb_tq = fallback['twitter_query']
            fb_params = fb_tq['params']

            self.config = {
                'crawl_interval': scrapers_config.get('crawl_interval', fallback['crawl_interval']),
                'source': scrapers_config.get('source', fallback['source']),
                'credentials': self._get_credentials(),
                'max_time_running': scrapers_config.get('max_time_running', fallback['max_time_running']),
                'threads': scrapers_config.get('threads', fallback['threads']),
                'twitter_query': {
                    'start_date': tq.get('start_date', fb_tq['start_date']),
                    'end_date': tq.get('end_date', fb_tq['end_date']),
                    'params': {
                        'filter': tq_params.get('filter', fb_params['filter']),
                        'lang': tq_params.get('lang', fb_params['lang']),
                        'keywords': tq_params.get('keywords', fb_params['keywords']),
                        'ticker': user_config.get('tickers', fb_params['ticker']),
                    },
                },
            }
            self._log(LogTypes.MESSAGE, f"Config loaded from DB (id={config_obj.config_id}).")

        except ObjectDoesNotExist:
            self._log(LogTypes.WARNING, 'No active Config in DB — using fallback defaults.')
            self.config = fallback
        except Exception as e:
            self._log(LogTypes.WARNING, f'Error loading DB config: {e} — using fallback defaults.')
            self.config = fallback

    def _gen_dates_pipeline(self) -> queue.Queue:
        """Generate dates from newest (end_date) to oldest (start_date)."""
        dates_pipeline: queue.Queue = queue.Queue()
        newest = datetime.strptime(
            self.config['twitter_query']['end_date'], '%Y-%m-%d',
        )
        oldest = datetime.strptime(
            self.config['twitter_query']['start_date'], '%Y-%m-%d',
        )

        current = newest
        while current >= oldest:
            dates_pipeline.put(current.strftime('%Y-%m-%d'))
            current -= timedelta(days=1)

        return dates_pipeline

    def get_scraper_config(self, config_id: int) -> dict:
        """Return the config_string for the given config_id."""
        try:
            Config = apps.get_model('scraper', 'Config')
            config_obj = Config.objects.get(pk=config_id)
            return config_obj.config_string
        except Config.DoesNotExist:
            raise ValueError(f"Config with ID {config_id} not found.")

    def _setup_instances(self) -> None:
        # Reuse existing browser session if still alive
        try:
            if getattr(self, 'instance', None):
                _ = self.instance.window_handles  # raises if session is dead
                self._log(LogTypes.MESSAGE, 'Reusing existing browser session.')
                return
        except Exception:
            self._log(LogTypes.WARNING, 'Previous browser session is dead — creating a new one.')
            self.instance = None

        try:
            from django.conf import settings as django_settings

            self._set_status(ScraperStates.SETTING_UP)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            )

            scraper_mode = os.getenv('SCRAPER_MODE', 'grid')
            grid_url = getattr(django_settings, 'SELENIUM_GRID_URL', None)

            if scraper_mode == 'local' or not grid_url:
                self.instance = webdriver.Chrome(options=chrome_options)
                self._log(LogTypes.MESSAGE, 'Using local Chrome browser.')
            else:
                self.instance = webdriver.Remote(
                    command_executor=grid_url,
                    options=chrome_options,
                )
                self._log(LogTypes.MESSAGE, f'Connected to Selenium Grid at {grid_url}')

            # Remove navigator.webdriver flag via CDP
            self.instance.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            self._log(LogTypes.ERROR, f"Failed to setup driver instance: {e}")
            raise

    def _page_says_error(self) -> bool:
        """Return True if the current page contains a rate-limit / try-again error."""
        try:
            body = self.instance.find_element(By.TAG_NAME, 'body').text.lower()
            return 'try again later' in body or 'something went wrong' in body
        except Exception:
            return False

    def _enter_identifier(self, value: str, label: str, max_retries: int = 5) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                field = WebDriverWait(self.instance, 15).until(
                    EC.presence_of_element_located((By.NAME, 'text')),
                )
                field.clear()
                field.send_keys(value)
                field.send_keys(Keys.RETURN)
                self._log(LogTypes.MESSAGE, f'{label} entered (attempt {attempt}).')
            except Exception as e:
                self._log(LogTypes.ERROR, f'Could not find text field for {label}: {e}')
                return False

            wait = 5 * attempt  # 5 s, 10 s, 15 s …
            time.sleep(wait)

            if not self._page_says_error():
                return True

            self._log(LogTypes.WARNING, f'"Try again later" after {label} — waiting {wait}s before retry.')

        self._log(LogTypes.ERROR, f'All retries exhausted for {label}.')
        return False

    def _enter_credentials(self) -> None:
        creds = self.config['credentials']

        identifier_sent = self._enter_identifier(creds['username'], 'username')
        if not identifier_sent:
            self._log(LogTypes.WARNING, 'Username failed — retrying with email as identifier.')
            identifier_sent = self._enter_identifier(creds['email'], 'email-as-identifier')
        if not identifier_sent:
            raise RuntimeError('Could not submit identifier — X.com keeps rate-limiting.')

        try:
            self.instance.find_element(By.NAME, 'password')
        except Exception:
            try:
                WebDriverWait(self.instance, 8).until(
                    EC.presence_of_element_located((By.NAME, 'text')),
                )
                self._log(LogTypes.MESSAGE, 'Verification step detected — entering email.')
                ok = self._enter_identifier(creds['email'], 'verification-email')
                if not ok:
                    raise RuntimeError('Verification step failed — retries exhausted.')
            except Exception as inner:
                # Could be the password field appearing late — let Step 3 handle it
                self._log(LogTypes.MESSAGE, f'Step-2 probe: {inner}')

        password_input = WebDriverWait(self.instance, 15).until(
            EC.presence_of_element_located((By.NAME, 'password')),
        )
        password_input.send_keys(creds['password'])
        password_input.send_keys(Keys.RETURN)

    def _generate_twitter_query(self, ticker: str, since_date: str, until_date: str) -> list[str]:
        try:
            qp = self.config['twitter_query']['params']
            filters = ' '.join(
                [f"-filter:{f}" for f in qp['filter']],
            )
            query = f"{ticker} lang:{qp['lang']} since:{since_date} until:{until_date} {filters}"
            return [query]
        except Exception as e:
            self._log(LogTypes.ERROR, f'Failed to generate query for {ticker}: {e}')
            return []

    def _is_logged_in(self) -> bool:
        """Check if browser has an active session — no navigation, just inspect state."""
        try:
            if not getattr(self, 'instance', None):
                return False
            _ = self.instance.window_handles
            logged_in = 'x.com/home' in self.instance.current_url
            if logged_in:
                self._log(LogTypes.MESSAGE, 'Existing session detected — skipping login.')
            return logged_in
        except Exception:
            return False

    def _accept_cookies(self) -> None:
        try:
            accept_btn = WebDriverWait(self.instance, 8).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(),'Accept all cookies') or contains(text(),'Accept cookies')]"),
                ),
            )
            accept_btn.click()
            self._log(LogTypes.MESSAGE, 'Cookie consent accepted.')
            time.sleep(2)
        except Exception:
            self._log(LogTypes.MESSAGE, 'No cookie banner found, continuing.')

    def _login_twitter(self) -> None:
        login_mode = os.getenv('LOGIN_MODE', 'auto')

        # Step 1: go to x.com, accept cookies
        self.instance.get('https://x.com')
        time.sleep(3)
        self._accept_cookies()

        if login_mode == 'manual':
            # Navigate to login page and wait for user
            self.instance.get('https://x.com/i/flow/login')
            self._log(
                LogTypes.MESSAGE,
                'Manual login mode — please log in via the browser. Waiting...',
            )
            while not self.stop_event.is_set():
                time.sleep(5)
                try:
                    if 'x.com/home' in self.instance.current_url:
                        self._log(LogTypes.MESSAGE, 'Manual login detected.')
                        return
                except Exception:
                    pass
            raise RuntimeError('Scraper stopped while waiting for manual login.')

        # Auto mode
        try:
            self.instance.get('https://x.com/i/flow/login')
            time.sleep(3)
            self._enter_credentials()
            self._wait_for_homepage()
            self._log(LogTypes.MESSAGE, 'Login successful.')
        except Exception as e:
            self._log(LogTypes.ERROR, f"Login failed: {e}")
            raise

    def _wait_for_homepage(self) -> None:
        try:
            WebDriverWait(self.instance, 20).until(
                lambda driver: 'x.com/home' in driver.current_url,
            )
            self._log(LogTypes.MESSAGE, 'Homepage loaded successfully.')
        except Exception as e:
            self._log(LogTypes.ERROR, f"Homepage did not load. URL: {self.instance.current_url}")
            raise

    def _extract_tweet_metadata(self, tweet_html: str) -> dict:
        soup = BeautifulSoup(tweet_html, 'html.parser')

        def extract_number_from_button(data_testid):
            button = soup.find('button', {'data-testid': data_testid})
            if button:
                try:
                    return int(button.get_text(strip=True).replace('K', '000').replace('M', '000000'))
                except ValueError:
                    pass
            return None

        likes = extract_number_from_button('like')
        retweets = extract_number_from_button('retweet')
        replies = extract_number_from_button('reply')

        views_div = soup.find(
            'a', {'aria-label': lambda x: x and 'views' in x.lower()},
        )
        views = None
        if views_div:
            aria_label = views_div['aria-label']
            try:
                views = int(
                    ''.join(filter(str.isdigit, aria_label.split('views')[0])),
                )
            except ValueError:
                views = None

        return {'likes': likes, 'retweets': retweets, 'replies': replies, 'views': views}


    def _parse_tweet(self, tweet_html, ticker: str) -> dict | None:
        """Extract text, date, and metadata from a single tweet article element.

        Returns a ready-to-enqueue dict, or None if the tweet should be skipped.
        """
        text_div = tweet_html.find('div', {'lang': 'en'})
        text = text_div.get_text(strip=True) if text_div else None
        time_el = tweet_html.find('time')
        date_str = time_el['datetime'] if time_el else None

        if not text or not date_str:
            self._log(LogTypes.WARNING, 'Skipping tweet due to missing text or date.')
            return None

        tweet_data = self._extract_tweet_metadata(str(tweet_html))
        tweet_data['ticker'] = ticker
        tweet_data['date'] = datetime.fromisoformat(date_str[:-1]).date()
        tweet_data['text'] = text
        tweet_data['source'] = self.config['source'][0]['name']
        return tweet_data

    def _scroll_and_collect(self, ticker: str) -> int:
        """Scroll the current search results page, parse tweets, and enqueue them.

        Returns the number of tweets collected.
        """
        count = 0
        seen: set[tuple[str, str]] = set()
        last_height = self.instance.execute_script('return document.body.scrollHeight')

        while True:
            if self.stop_event.is_set():
                break

            self.instance.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(5)
            new_height = self.instance.execute_script('return document.body.scrollHeight')

            if new_height == last_height:
                try:
                    latest_button = self.instance.find_element(
                        By.XPATH, "//span[text()='Latest']",
                    )
                    latest_button.click()
                    time.sleep(2)
                except Exception:
                    break

            last_height = new_height
            page_source = self.instance.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            articles = soup.find_all('article', {'data-testid': 'tweet'})

            for article in articles:
                try:
                    tweet_data = self._parse_tweet(article, ticker)
                    if tweet_data is None:
                        continue

                    fingerprint = (tweet_data['text'], str(tweet_data['date']))
                    if fingerprint in seen:
                        continue
                    seen.add(fingerprint)

                    enqueue_scraper_data(tweet_data)
                    count += 1
                    self._update_task({'count': count})
                except KeyError as e:
                    self._log(LogTypes.ERROR, f'Missing key while processing tweet: {e}')
                except ValueError as e:
                    self._log(LogTypes.ERROR, f'Value error processing tweet: {e}')
                except Exception as e:
                    self._log(LogTypes.ERROR, f'Unexpected error processing tweet: {e}')

        return count

    def _scrape_ticker(self, ticker: str, since_date: str, until_date: str) -> int:
        """Search for a single ticker on a single day and collect all tweets.

        Returns the number of tweets found.
        """
        queries = self._generate_twitter_query(
            ticker=ticker, since_date=since_date, until_date=until_date,
        )
        if not queries:
            self._log(LogTypes.ERROR, f'No query generated for {ticker}, skipping.')
            return 0

        url = self.config['source'][0]['base_url'] + quote_plus(queries[0])
        self.instance.get(url)
        WebDriverWait(self.instance, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete',
        )

        return self._scroll_and_collect(ticker)

    def _wait_if_paused(self) -> bool:
        """Block while paused. Returns False if stop was requested during the wait."""
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(1)
        return not self.stop_event.is_set()

    def run_procedure(self, crawling_mode=True):
        self.load_config()
        self._setup_instances()
        if not self._is_logged_in():
            self._login_twitter()
        self._set_status(ScraperStates.RUNNING)

        while not self.stop_event.is_set():
            if not self._wait_if_paused():
                break

            if crawling_mode and self.state == ScraperStates.RUNNING:
                dates_pipeline = self._gen_dates_pipeline()
                tickers_list = self.config['twitter_query']['params']['ticker']

                while not dates_pipeline.empty() and not self.stop_event.is_set():
                    current_date = dates_pipeline.get()
                    next_date = (
                        datetime.strptime(current_date, '%Y-%m-%d') + timedelta(days=1)
                    ).strftime('%Y-%m-%d')

                    self._log(LogTypes.MESSAGE, f'Scraping date: {current_date}')

                    for ticker in tickers_list:
                        if self.stop_event.is_set():
                            break
                        if not self._wait_if_paused():
                            break

                        self._update_task({
                            'source': self.config['source'][0]['name'],
                            'date': current_date,
                            'ticker': ticker,
                            'count': 0,
                        }, overwrite=True)

                        count = self._scrape_ticker(ticker, current_date, next_date)
                        self._log(
                            LogTypes.MESSAGE,
                            f"Found {count} tweets for '{ticker}' on {current_date}",
                        )

                # All dates exhausted — wait before next crawl cycle
                time.sleep(self.config['crawl_interval'])

            else:
                time.sleep(1)

        self._log(LogTypes.MESSAGE, 'Scraper stopped. Browser session preserved.')

    ## GETTERS ###

    def get_source(self):
        return self.config['source']
