from django.db import models
from scraper.models import Config
from tickers.models import Ticker

class Signal(models.Model):
    signal_id = models.AutoField(primary_key=True, unique=True)
    signal_type = models.CharField(max_length=32)
    ticker_id = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    confidence_score = models.FloatField()
    generated_at = models.DateTimeField(auto_now_add=True)
    used_model = models.CharField(max_length=64)
    config_ig = models.ForeignKey(Config, on_delete=models.CASCADE)
