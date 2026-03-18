from django.db import models
from tickers.models import Ticker
from .source import Source
from .content import Content

class PostMeta(models.Model):
    meta_id = models.AutoField(primary_key=True)
    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True,
    )
    likes = models.PositiveIntegerField(null=True, blank=True)
    views = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)
    comments = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(likes__gte=0), name='likes_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(views__gte=0), name='views_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(shares__gte=0), name='shares_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(comments__gte=0), name='comments_nonnegative',
            ),
        ]

class PostPrediction(models.Model):
    prediction_id = models.AutoField(primary_key=True)
    prediction = models.PositiveSmallIntegerField()
    probabilities = models.JSONField()
    model_name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

class Post(models.Model):
    post_id = models.AutoField(primary_key=True)
    time_stamp = models.DateTimeField(db_index=True)
    related_ticker = models.ForeignKey(
        Ticker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
    )
    related_content = models.ForeignKey(Content, on_delete=models.CASCADE)
    post_metadata = models.ForeignKey(PostMeta, on_delete=models.CASCADE)
    post_prediction = models.ForeignKey(
        PostPrediction, on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ['-time_stamp']
        unique_together = ('related_ticker', 'time_stamp', 'related_content')
        indexes = [
            models.Index(fields=['related_ticker', 'time_stamp']),
        ]
