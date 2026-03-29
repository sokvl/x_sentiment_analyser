from django.test import TestCase
from django.db import IntegrityError

from scraper.models import Config
from tickers.models import Ticker
from signals.models import Signal


class SignalModelTests(TestCase):
    def setUp(self):
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.config = Config.objects.create(
            name='test_config',
            active=True,
            config_string={'user_config': {}, 'scrapers_config': []},
        )

    def test_create_signal(self):
        signal = Signal.objects.create(
            signal_type='BUY',
            ticker_id=self.ticker,
            confidence_score=0.85,
            used_model='LSTMCNNv1',
            config_ig=self.config,
        )
        self.assertEqual(signal.signal_type, 'BUY')
        self.assertEqual(signal.confidence_score, 0.85)
        self.assertEqual(signal.ticker_id, self.ticker)
        self.assertIsNotNone(signal.generated_at)

    def test_signal_types(self):
        for signal_type in ['BUY', 'SELL', 'HOLD']:
            signal = Signal.objects.create(
                signal_type=signal_type,
                ticker_id=self.ticker,
                confidence_score=0.5,
                used_model='LSTMCNNv1',
                config_ig=self.config,
            )
            self.assertEqual(signal.signal_type, signal_type)

    def test_signal_auto_generates_id(self):
        signal = Signal.objects.create(
            signal_type='BUY',
            ticker_id=self.ticker,
            confidence_score=0.5,
            used_model='test',
            config_ig=self.config,
        )
        self.assertIsNotNone(signal.signal_id)

    def test_cascade_delete_on_ticker(self):
        Signal.objects.create(
            signal_type='BUY',
            ticker_id=self.ticker,
            confidence_score=0.5,
            used_model='test',
            config_ig=self.config,
        )
        self.ticker.delete()
        self.assertEqual(Signal.objects.count(), 0)

    def test_cascade_delete_on_config(self):
        Signal.objects.create(
            signal_type='SELL',
            ticker_id=self.ticker,
            confidence_score=-0.3,
            used_model='test',
            config_ig=self.config,
        )
        self.config.delete()
        self.assertEqual(Signal.objects.count(), 0)
