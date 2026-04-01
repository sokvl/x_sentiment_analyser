from django.test import TestCase

from scraper.models import Config
from tickers.models import Ticker
from signals.models import Signal
from signals.serializers import SignalSerializer


class SignalSerializerTests(TestCase):
    def setUp(self):
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.config = Config.objects.create(
            name='test', active=True,
            config_string={'user_config': {}, 'scrapers_config': []},
        )
        self.signal = Signal.objects.create(
            signal_type='BUY', ticker=self.ticker,
            confidence_score=0.85, used_model='LSTMCNNv1', config=self.config,
        )

    def test_serializes_expected_fields(self):
        serializer = SignalSerializer(self.signal)
        data = serializer.data
        self.assertIn('signal_id', data)
        self.assertIn('signal_type', data)
        self.assertIn('ticker', data)
        self.assertIn('confidence_score', data)
        self.assertIn('generated_at', data)
        self.assertIn('used_model', data)
        self.assertIn('config', data)

    def test_read_only_fields(self):
        serializer = SignalSerializer(self.signal)
        data = serializer.data
        self.assertEqual(data['signal_id'], self.signal.signal_id)
        self.assertIsNotNone(data['generated_at'])

    def test_deserialization(self):
        data = {
            'signal_type': 'SELL',
            'ticker': self.ticker.ticker_id,
            'confidence_score': -0.5,
            'used_model': 'TransformerV2',
            'config': self.config.config_id,
        }
        serializer = SignalSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
