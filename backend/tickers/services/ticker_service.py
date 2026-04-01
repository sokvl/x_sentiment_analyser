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
