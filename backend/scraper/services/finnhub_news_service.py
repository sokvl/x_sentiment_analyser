from __future__ import annotations

import logging
from datetime import date, datetime, timezone as dt_timezone

import finnhub
from django.conf import settings

from stocknlp.tasks import enqueue_finnhub_news

logger = logging.getLogger(__name__)


class FinnhubNewsService:
    def _build_text(self, headline: str, summary: str) -> str:
        headline = headline or ''
        summary = summary or ''
        return f"{headline}. {summary}".strip() if summary else headline

    def fetch_and_enqueue(self, symbols: list[str], from_date: date, to_date: date) -> int:
        if not symbols:
            return 0

        client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
        queued = 0

        for symbol in symbols:
            try:
                articles = client.company_news(
                    symbol, _from=from_date.isoformat(), to=to_date.isoformat(),
                ) or []
            except Exception as e:
                logger.exception("Finnhub fetch failed for %s: %s", symbol, e)
                continue

            for item in articles:
                if item.get('id') is None:
                    continue
                enqueue_finnhub_news({
                    'text': self._build_text(item.get('headline'), item.get('summary')),
                    'ticker': symbol,
                    'headline': item.get('headline', ''),
                    'summary': item.get('summary', ''),
                    'url': item.get('url', ''),
                    'publisher': item.get('source', ''),
                    'news_category': item.get('category', ''),
                    'external_id': str(item['id']),
                    'published_at': datetime.fromtimestamp(item['datetime'], tz=dt_timezone.utc),
                })
                queued += 1

        return queued
