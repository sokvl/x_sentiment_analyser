from __future__ import annotations

from django.db import models
from scraper.models import Config
from tickers.models import Ticker


class Signal(models.Model):
    signal_id = models.AutoField(primary_key=True, unique=True)
    signal_type = models.CharField()
    ticker_id = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    confidence_score = models.FloatField()
    generated_at = models.DateTimeField()
    used_model = models.CharField()
    config_ig = models.ForeignKey(Config, on_delete=models.CASCADE)
