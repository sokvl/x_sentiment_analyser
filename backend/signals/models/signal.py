from django.db import models
from scraper.models import Config
from tickers.models import Ticker


class Signal(models.Model):
    signal_id = models.AutoField(primary_key=True)
    signal_type = models.CharField(max_length=32)
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    confidence_score = models.FloatField()
    generated_at = models.DateTimeField(auto_now_add=True)
    used_model = models.CharField(max_length=64)
    config = models.ForeignKey(Config, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['generated_at']),
            models.Index(fields=['ticker', 'generated_at']),
        ]

    def __str__(self):
        return f"{self.signal_type} {self.ticker_id} @ {self.confidence_score}"
