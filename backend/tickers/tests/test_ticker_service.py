from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import ValidationError, NotFound

from tickers.models import Ticker
from tickers.services.ticker_service import TickerService


class ResolveTickersTests(TestCase):
    def setUp(self):
        self.service = TickerService()
        self.ticker1 = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.ticker2 = Ticker.objects.create(
            symbol='TSLA', type='stock', full_name='Tesla Inc.'
        )

    def test_resolves_all(self):
        symbols, qs = self.service.resolve_tickers('all')
        self.assertEqual(set(symbols), {'AAPL', 'TSLA'})
        self.assertEqual(qs.count(), 2)

    def test_resolves_specific_tickers(self):
        symbols, qs = self.service.resolve_tickers('AAPL')
        self.assertEqual(symbols, ['AAPL'])
        self.assertEqual(qs.count(), 1)

    def test_resolves_comma_separated(self):
        symbols, qs = self.service.resolve_tickers('AAPL,TSLA')
        self.assertEqual(set(symbols), {'AAPL', 'TSLA'})

    def test_raises_not_found_for_unknown_ticker(self):
        with self.assertRaises(NotFound):
            self.service.resolve_tickers('UNKNOWN')

    def test_raises_not_found_when_db_empty(self):
        Ticker.objects.all().delete()
        with self.assertRaises(NotFound):
            self.service.resolve_tickers('all')


class ParseDateRangeTests(TestCase):
    def setUp(self):
        self.service = TickerService()

    def test_parses_valid_dates(self):
        start, end = self.service.parse_date_range('2024-01-01', '2024-01-31')
        self.assertEqual(start, date(2024, 1, 1))
        self.assertEqual(end, date(2024, 2, 1))  # end + 1 day (yfinance exclusive)

    def test_defaults_end_to_today(self):
        start, end = self.service.parse_date_range('2024-01-01', None)
        self.assertEqual(end, date.today() + timedelta(days=1))

    def test_defaults_start_to_end(self):
        start, end = self.service.parse_date_range(None, '2024-06-15')
        self.assertEqual(start, date(2024, 6, 15))
        self.assertEqual(end, date(2024, 6, 16))  # end + 1 day (yfinance exclusive)

    def test_invalid_date_format_raises(self):
        with self.assertRaises(ValidationError):
            self.service.parse_date_range('bad-date', '2024-01-31')

    def test_invalid_end_date_raises(self):
        with self.assertRaises(ValidationError):
            self.service.parse_date_range('2024-01-01', 'bad')


class FetchStockDataTests(TestCase):
    def setUp(self):
        self.service = TickerService()

    def test_returns_empty_dict_for_no_symbols(self):
        result = self.service.fetch_stock_data([], date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(result, {})

    @patch('django.core.cache.cache')
    @patch('tickers.services.ticker_service.yf')
    def test_returns_cached_data(self, mock_yf, mock_cache):
        mock_cache.get.return_value = {'AAPL': [{'Open': 150}]}
        result = self.service.fetch_stock_data(['AAPL'], date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(result, {'AAPL': [{'Open': 150}]})
        mock_yf.download.assert_not_called()

    @patch('django.core.cache.cache')
    @patch('tickers.services.ticker_service.yf')
    def test_fetches_from_yfinance_on_cache_miss(self, mock_yf, mock_cache):
        mock_cache.get.return_value = None
        import pandas as pd
        mock_df = pd.DataFrame({
            'Open': [150.0], 'Close': [155.0],
            'High': [156.0], 'Low': [149.0], 'Volume': [1000000]
        }, index=pd.DatetimeIndex([date(2024, 1, 2)]))
        mock_yf.download.return_value = mock_df

        result = self.service.fetch_stock_data(['AAPL'], date(2024, 1, 1), date(2024, 1, 31))
        self.assertIn('AAPL', result)
        mock_yf.download.assert_called_once()

    @patch('django.core.cache.cache')
    @patch('tickers.services.ticker_service.yf')
    def test_handles_yfinance_exception(self, mock_yf, mock_cache):
        mock_cache.get.return_value = None
        mock_yf.download.side_effect = Exception("API error")

        result = self.service.fetch_stock_data(['AAPL'], date(2024, 1, 1), date(2024, 1, 31))
        self.assertIn('AAPL', result)
        self.assertIn('error', result['AAPL'])

    @patch('django.core.cache.cache')
    @patch('tickers.services.ticker_service.yf')
    def test_handles_empty_dataframe(self, mock_yf, mock_cache):
        mock_cache.get.return_value = None
        import pandas as pd
        mock_yf.download.return_value = pd.DataFrame()

        result = self.service.fetch_stock_data(['AAPL'], date(2024, 1, 1), date(2024, 1, 31))
        self.assertIn('AAPL', result)
        self.assertIn('error', result['AAPL'])
