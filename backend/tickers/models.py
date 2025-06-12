from __future__ import annotations

from django.db import models


class Ticker(models.Model):
    ticker_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=32, db_index=True)
    symbol = models.CharField(max_length=8, unique=True, db_index=True)
    full_name = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']
        indexes = [models.Index(fields=['type', 'symbol'])]

    def __str__(self):
        return self.symbol
