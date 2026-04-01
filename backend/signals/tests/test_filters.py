from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from scraper.models import Config
from tickers.models import Ticker
from signals.models import Signal
from signals.filters import SignalFilter


class SignalFilterTests(TestCase):
    def setUp(self):
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.ticker2 = Ticker.objects.create(
            symbol='TSLA', type='stock', full_name='Tesla Inc.'
        )
        self.config = Config.objects.create(
            name='test', active=True,
            config_string={'user_config': {}, 'scrapers_config': []},
        )
        self.signal1 = Signal.objects.create(
            signal_type='BUY', ticker=self.ticker,
            confidence_score=0.5, used_model='test', config=self.config,
        )
        self.signal2 = Signal.objects.create(
            signal_type='SELL', ticker=self.ticker2,
            confidence_score=-0.3, used_model='test', config=self.config,
        )

    def test_filter_by_ticker_id(self):
        f = SignalFilter({'ticker_id': self.ticker.ticker_id}, queryset=Signal.objects.all())
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().signal_type, 'BUY')

    def test_filter_by_start_date(self):
        future = (timezone.now() + timedelta(days=1)).date().isoformat()
        f = SignalFilter({'start_date': future}, queryset=Signal.objects.all())
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_end_date(self):
        future = (timezone.now() + timedelta(days=1)).date().isoformat()
        f = SignalFilter({'end_date': future}, queryset=Signal.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_no_filters_returns_all(self):
        f = SignalFilter({}, queryset=Signal.objects.all())
        self.assertEqual(f.qs.count(), 2)
