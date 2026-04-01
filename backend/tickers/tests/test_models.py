from django.test import TestCase
from django.db import IntegrityError

from tickers.models import Ticker


class TickerModelTests(TestCase):
    def test_create_ticker(self):
        ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.assertEqual(ticker.symbol, 'AAPL')
        self.assertEqual(ticker.type, 'stock')
        self.assertEqual(ticker.full_name, 'Apple Inc.')
        self.assertIsNotNone(ticker.created_at)
        self.assertIsNotNone(ticker.updated_at)

    def test_str_returns_symbol(self):
        ticker = Ticker.objects.create(
            symbol='TSLA', type='stock', full_name='Tesla Inc.'
        )
        self.assertEqual(str(ticker), 'TSLA')

    def test_symbol_unique(self):
        Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple Inc.')
        with self.assertRaises(IntegrityError):
            Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple 2')

    def test_full_name_allows_duplicates(self):
        Ticker.objects.create(symbol='GOOG', type='stock', full_name='Alphabet Inc.')
        Ticker.objects.create(symbol='GOOGL', type='stock', full_name='Alphabet Inc.')
        self.assertEqual(Ticker.objects.filter(full_name='Alphabet Inc.').count(), 2)

    def test_default_ordering_by_symbol(self):
        Ticker.objects.create(symbol='TSLA', type='stock', full_name='Tesla Inc.')
        Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple Inc.')
        Ticker.objects.create(symbol='MSFT', type='stock', full_name='Microsoft Corp.')
        symbols = list(Ticker.objects.values_list('symbol', flat=True))
        self.assertEqual(symbols, ['AAPL', 'MSFT', 'TSLA'])

    def test_auto_primary_key(self):
        ticker = Ticker.objects.create(
            symbol='GOOG', type='stock', full_name='Alphabet Inc.'
        )
        self.assertIsNotNone(ticker.ticker_id)
