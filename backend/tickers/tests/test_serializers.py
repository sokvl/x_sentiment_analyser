from django.test import TestCase

from tickers.models import Ticker
from tickers.serializers import TickerSerializer


class TickerSerializerTests(TestCase):
    def test_serializes_all_fields(self):
        ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        serializer = TickerSerializer(ticker)
        data = serializer.data
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertEqual(data['type'], 'stock')
        self.assertEqual(data['full_name'], 'Apple Inc.')
        self.assertIn('ticker_id', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_valid_deserialization(self):
        data = {'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'}
        serializer = TickerSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_required_field(self):
        data = {'type': 'stock'}
        serializer = TickerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('symbol', serializer.errors)

    def test_read_only_fields_ignored_on_input(self):
        data = {
            'ticker_id': 999,
            'symbol': 'GOOG',
            'type': 'stock',
            'full_name': 'Alphabet Inc.',
        }
        serializer = TickerSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticker = serializer.save()
        self.assertNotEqual(ticker.ticker_id, 999)
