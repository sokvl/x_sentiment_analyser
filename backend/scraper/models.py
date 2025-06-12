from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from tickers.models import Ticker


class Content(models.Model):
    """Raw article / tweet text."""
    content_id = models.AutoField(primary_key=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['created_at'])]


class Config(models.Model):
    config_id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=64)
    active = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    uptaded_at = models.DateTimeField(auto_now=True)
    config_string = models.JSONField()


class Source(models.Model):
    source_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64, unique=True)
    base_url = models.URLField(blank=True)
    login_required = models.BooleanField(default=False)
    credentials_id = models.IntegerField(blank=True, null=True)
    category = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class PostMeta(models.Model):
    meta_id = models.AutoField(primary_key=True)
    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True,
    )
    likes = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    views = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    shares = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    comments = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    likes__gte=0,
                ), name='likes_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(
                    views__gte=0,
                ), name='views_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(
                    shares__gte=0,
                ), name='shares_nonnegative',
            ),
            models.CheckConstraint(
                check=models.Q(
                    comments__gte=0,
                ), name='comments_nonnegative',
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
