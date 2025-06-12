# signals/utils.py
from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import yfinance as yf
from django.apps import apps


def safe_round(value, decimals=2):
    if value != value or value in [float('inf'), float('-inf')]:
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


def fetch_historical_data(tickers, period='max'):
    return yf.download(tickers, period=period, progress=False, group_by=tickers)


def date_range(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)
