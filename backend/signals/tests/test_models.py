from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.db import IntegrityError

from scraper.models import Config
from tickers.models import Ticker
from signals.models import Signal, UploadedFile


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
            ticker=self.ticker,
            confidence_score=0.85,
            used_model='LSTMCNNv1',
            config=self.config,
        )
        self.assertEqual(signal.signal_type, 'BUY')
        self.assertEqual(signal.confidence_score, 0.85)
        self.assertEqual(signal.ticker, self.ticker)
        self.assertIsNotNone(signal.generated_at)

    def test_signal_types(self):
        for signal_type in ['BUY', 'SELL', 'HOLD']:
            signal = Signal.objects.create(
                signal_type=signal_type,
                ticker=self.ticker,
                confidence_score=0.5,
                used_model='LSTMCNNv1',
                config=self.config,
            )
            self.assertEqual(signal.signal_type, signal_type)

    def test_signal_auto_generates_id(self):
        signal = Signal.objects.create(
            signal_type='BUY',
            ticker=self.ticker,
            confidence_score=0.5,
            used_model='test',
            config=self.config,
        )
        self.assertIsNotNone(signal.signal_id)

    def test_cascade_delete_on_ticker(self):
        Signal.objects.create(
            signal_type='BUY',
            ticker=self.ticker,
            confidence_score=0.5,
            used_model='test',
            config=self.config,
        )
        self.ticker.delete()
        self.assertEqual(Signal.objects.count(), 0)

    def test_cascade_delete_on_config(self):
        Signal.objects.create(
            signal_type='SELL',
            ticker=self.ticker,
            confidence_score=-0.3,
            used_model='test',
            config=self.config,
        )
        self.config.delete()
        self.assertEqual(Signal.objects.count(), 0)


class UploadedFileModelTests(TestCase):
    def _make_file(self, **kwargs):
        defaults = {
            'display_name': 'demo.csv',
            'file': SimpleUploadedFile('demo.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n'),
        }
        defaults.update(kwargs)
        instance = UploadedFile.objects.create(**defaults)
        self.addCleanup(instance.file.delete, save=False)
        return instance

    def test_defaults_to_not_interviewer_visible(self):
        instance = self._make_file()
        self.assertFalse(instance.is_interviewer_visible)

    def test_row_count_defaults_to_none(self):
        instance = self._make_file()
        self.assertIsNone(instance.row_count)

    def test_str_returns_display_name(self):
        instance = self._make_file(display_name='my_file.csv')
        self.assertEqual(str(instance), 'my_file.csv')

    def test_ordering_is_newest_first(self):
        older = self._make_file(display_name='older.csv')
        newer = self._make_file(display_name='newer.csv')
        self.assertEqual(list(UploadedFile.objects.all()), [newer, older])
