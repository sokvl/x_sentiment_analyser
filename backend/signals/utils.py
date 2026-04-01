# signals/utils.py
from __future__ import annotations

import math
from datetime import datetime
from datetime import timedelta

import yfinance as yf
from django.apps import apps


def safe_round(value, decimals=2):
    if not math.isfinite(value):
        return None
    return round(value, decimals)


def parse_date(date_str, format='%Y-%m-%d'):
    try:
        return datetime.strptime(date_str, format).date()
    except ValueError:
        return None


def get_data_manager():
    try:
        return apps.get_app_config('scraper').DATA_MANAGER, None
    except AttributeError as e:
        return None, str(e)


def fetch_historical_data(tickers, start=None, end=None):
    kwargs = {'progress': False, 'group_by': tickers}
    if start and end:
        kwargs['start'] = start.isoformat()
        kwargs['end'] = end.isoformat()
    else:
        kwargs['period'] = 'max'
    return yf.download(tickers, **kwargs)


def date_range(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)
