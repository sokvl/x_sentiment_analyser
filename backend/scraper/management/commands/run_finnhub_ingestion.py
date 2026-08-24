from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from scraper.services.finnhub_news_service import FinnhubNewsService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Periodically fetch Finnhub news for the active config's tickers and score it via FinBERT"

    def handle(self, *args, **options):
        interval = settings.FINNHUB_FETCH_INTERVAL_SECONDS
        service = FinnhubNewsService()

        while True:
            try:
                Config = apps.get_app_config('scraper').get_model('Config')
                config = Config.objects.filter(active=True).first()
                tickers = (
                    config.config_string.get('user_config', {}).get('tickers', [])
                    if config else []
                )

                if tickers:
                    to_date = datetime.now().date()
                    from_date = to_date - timedelta(days=1)
                    queued = service.fetch_and_enqueue(tickers, from_date, to_date)
                    self.stdout.write(f"Finnhub ingestion: queued {queued} articles")
                else:
                    self.stdout.write("Finnhub ingestion: no tickers configured, skipping cycle")
            except Exception:
                logger.exception('Finnhub ingestion cycle failed')

            time.sleep(interval)
