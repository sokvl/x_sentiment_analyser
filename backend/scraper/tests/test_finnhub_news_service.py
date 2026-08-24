from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase

from scraper.services.finnhub_news_service import FinnhubNewsService


class BuildTextTests(TestCase):
    def setUp(self):
        self.service = FinnhubNewsService()

    def test_combines_headline_and_summary(self):
        text = self.service._build_text('Headline', 'Summary')
        self.assertEqual(text, 'Headline. Summary')

    def test_falls_back_to_headline_when_summary_empty(self):
        text = self.service._build_text('Headline', '')
        self.assertEqual(text, 'Headline')

    def test_handles_none_values(self):
        text = self.service._build_text(None, None)
        self.assertEqual(text, '')


class FetchAndEnqueueTests(TestCase):
    def setUp(self):
        self.service = FinnhubNewsService()
        self.from_date = date(2026, 1, 1)
        self.to_date = date(2026, 1, 2)
        self.article = {
            'id': 25341,
            'headline': 'Apple news',
            'summary': 'Apple summary',
            'url': 'https://example.com/article',
            'source': 'TheStreet',
            'category': 'company news',
            'datetime': 1735689600,
        }

    def test_returns_zero_for_no_symbols(self):
        self.assertEqual(self.service.fetch_and_enqueue([], self.from_date, self.to_date), 0)

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_enqueues_one_job_per_article(self, mock_finnhub, mock_enqueue):
        mock_finnhub.Client.return_value.company_news.return_value = [self.article]

        queued = self.service.fetch_and_enqueue(['AAPL'], self.from_date, self.to_date)

        self.assertEqual(queued, 1)
        mock_enqueue.assert_called_once()
        payload = mock_enqueue.call_args[0][0]
        self.assertEqual(payload['ticker'], 'AAPL')
        self.assertEqual(payload['external_id'], '25341')
        self.assertEqual(payload['text'], 'Apple news. Apple summary')

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_handles_empty_response(self, mock_finnhub, mock_enqueue):
        mock_finnhub.Client.return_value.company_news.return_value = []

        queued = self.service.fetch_and_enqueue(['AAPL'], self.from_date, self.to_date)

        self.assertEqual(queued, 0)
        mock_enqueue.assert_not_called()

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_handles_none_response(self, mock_finnhub, mock_enqueue):
        mock_finnhub.Client.return_value.company_news.return_value = None

        queued = self.service.fetch_and_enqueue(['AAPL'], self.from_date, self.to_date)

        self.assertEqual(queued, 0)
        mock_enqueue.assert_not_called()

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_skips_articles_without_id(self, mock_finnhub, mock_enqueue):
        mock_finnhub.Client.return_value.company_news.return_value = [
            {**self.article, 'id': None},
        ]

        queued = self.service.fetch_and_enqueue(['AAPL'], self.from_date, self.to_date)

        self.assertEqual(queued, 0)
        mock_enqueue.assert_not_called()

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_one_ticker_failure_does_not_stop_others(self, mock_finnhub, mock_enqueue):
        client = mock_finnhub.Client.return_value

        def side_effect(symbol, **kwargs):
            if symbol == 'AAPL':
                raise Exception('API error')
            return [self.article]

        client.company_news.side_effect = side_effect

        queued = self.service.fetch_and_enqueue(['AAPL', 'TSLA'], self.from_date, self.to_date)

        self.assertEqual(queued, 1)
        mock_enqueue.assert_called_once()

    @patch('scraper.services.finnhub_news_service.enqueue_finnhub_news')
    @patch('scraper.services.finnhub_news_service.finnhub')
    def test_all_tickers_failing_returns_zero(self, mock_finnhub, mock_enqueue):
        mock_finnhub.Client.return_value.company_news.side_effect = Exception('API error')

        queued = self.service.fetch_and_enqueue(['AAPL', 'TSLA'], self.from_date, self.to_date)

        self.assertEqual(queued, 0)
        mock_enqueue.assert_not_called()
