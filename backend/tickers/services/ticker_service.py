from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf
from pandas import MultiIndex
from django.conf import settings
from rest_framework.exceptions import ValidationError, NotFound

from ..models import Ticker

logger = logging.getLogger(__name__)


class TickerService:
    """
    Encapsulates all business logic for ticker data resolution and
    external market data fetching.
    """

    def resolve_tickers(self, tickers_param: str) -> tuple[list[str], any]:
        """
        Resolves a 'tickers' query parameter ("all" or "TSLA,AAPL,...") to
        a validated list of symbols and a matching queryset.

        Returns: (symbol_list, queryset)
        Raises: NotFound if no valid tickers are found in the database.
        """
        if tickers_param == 'all':
            queryset = Ticker.objects.all()
            # Strip leading '$' convention if used (e.g. "$TSLA" → "TSLA")
            symbols = [t.symbol.lstrip('$') for t in queryset]
        else:
            requested = [s.strip() for s in tickers_param.split(',')]
            queryset = Ticker.objects.filter(symbol__in=requested)
            symbols = list(queryset.values_list('symbol', flat=True))

        if not symbols:
            raise NotFound("No valid tickers found in the database.")

        return symbols, queryset

    def parse_date_range(self, start_date: str | None, end_date: str | None) -> tuple[date, date]:
        """
        Parses and validates start/end date strings (YYYY-MM-DD).
        Defaults end_date to today, start_date to end_date.
        Raises: ValidationError on bad format.
        """
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else datetime.now().date()
            start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else end
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

        # yfinance 'end' param is exclusive, so add one day to include it
        return start, end + timedelta(days=1)

    def fetch_stock_data(self, symbols: list[str], start_date: date, end_date: date) -> dict:
        """
        Fetches OHLCV data for all symbols in a SINGLE yfinance call.
        Results are cached per (symbol_set, date_range) for 60 minutes.
        Returns a dict keyed by symbol.
        """
        from django.core.cache import cache
        from django.conf import settings

        if not symbols:
            return {}

        cache_key = f"stock:{'_'.join(sorted(symbols))}:{start_date}:{end_date}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT: %s", cache_key)
            return cached

        try:
            raw = yf.download(
                tickers=' '.join(symbols),
                start=start_date,
                end=end_date,
                group_by='ticker',
                progress=False,
                auto_adjust=True,
                timeout=settings.YFINANCE_TIMEOUT_SECONDS,
            )
        except Exception as e:
            logger.exception("yfinance bulk download failed: %s", e)
            return {symbol: {'error': f"Failed to fetch data: {e}"} for symbol in symbols}

        if raw.empty:
            return {symbol: {'error': 'No data found for the given date range.'} for symbol in symbols}

        result = {}
        for symbol in symbols:
            try:
                if isinstance(raw.columns, MultiIndex):
                    data = raw[symbol] if symbol in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    data = raw

                if data.empty:
                    result[symbol] = {'error': 'No price data found for this ticker.'}
                else:
                    result[symbol] = data.reset_index().to_dict(orient='records')
            except Exception as e:
                logger.exception("Error parsing data for %s: %s", symbol, e)
                result[symbol] = {'error': f"Error parsing data: {e}"}

        cache.set(cache_key, result, timeout=settings.CACHE_TTL_STOCK_DATA)
        logger.debug("Cache SET: %s (%ss TTL)", cache_key, settings.CACHE_TTL_STOCK_DATA)
        return result

    def parse_news_count(self, count_param: str | None) -> int:
        """
        Parses and validates the 'count' query param (default 5, 1-50).
        Raises: ValidationError on bad value.
        """
        if count_param is None:
            return 5

        try:
            count = int(count_param)
        except ValueError:
            raise ValidationError("Invalid count. Must be an integer.")

        if count < 1 or count > 50:
            raise ValidationError("Invalid count. Must be between 1 and 50.")

        return count

    def _normalize_news_item(self, item: dict, symbol: str) -> dict:
        content = item.get('content', {})
        return {
            'ticker': symbol,
            'title': content.get('title'),
            'publisher': (content.get('provider') or {}).get('displayName'),
            'link': (content.get('canonicalUrl') or {}).get('url'),
            'published_at': content.get('pubDate'),
        }

    def fetch_news(self, symbols: list[str], count: int) -> dict:
        """
        Fetches recent news headlines per symbol from yfinance.
        Results are cached per (symbol_set, count) for CACHE_TTL_NEWS seconds.
        Returns a dict keyed by symbol.
        """
        from django.core.cache import cache

        if not symbols:
            return {}

        cache_key = f"news:{'_'.join(sorted(symbols))}:{count}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT: %s", cache_key)
            return cached

        result = {}
        for symbol in symbols:
            try:
                raw_items = yf.Ticker(symbol).news[:count]
                result[symbol] = [self._normalize_news_item(item, symbol) for item in raw_items]
            except Exception as e:
                logger.exception("yfinance news fetch failed for %s: %s", symbol, e)
                result[symbol] = {'error': f"Failed to fetch news: {e}"}

        cache.set(cache_key, result, timeout=settings.CACHE_TTL_NEWS)
        logger.debug("Cache SET: %s (%ss TTL)", cache_key, settings.CACHE_TTL_NEWS)
        return result
