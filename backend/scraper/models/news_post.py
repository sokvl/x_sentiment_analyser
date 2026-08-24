from django.db import models
from tickers.models import Ticker
from .post import PostPrediction

class NewsPost(models.Model):
    news_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    ticker = models.ForeignKey(
        Ticker, on_delete=models.SET_NULL, null=True, blank=True, related_name='news_posts',
    )
    headline = models.TextField()
    summary = models.TextField(blank=True)
    text = models.TextField()
    url = models.URLField(blank=True)
    publisher = models.CharField(max_length=128, blank=True)
    category = models.CharField(max_length=64, blank=True)
    published_at = models.DateTimeField(db_index=True)
    news_prediction = models.ForeignKey(PostPrediction, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['ticker', 'published_at']),
        ]
