from __future__ import annotations

import hashlib
import secrets

from django.db import models
from django.utils import timezone


class InterviewerKey(models.Model):
    key_id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=128)
    prefix = models.CharField(max_length=12, unique=True, db_index=True)
    hashed_secret = models.CharField(max_length=64)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.label} ({self.prefix})'

    @staticmethod
    def hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    @classmethod
    def create_key(cls, label: str, expires_at=None) -> tuple['InterviewerKey', str]:
        prefix = secrets.token_hex(4)
        secret = secrets.token_urlsafe(32)
        instance = cls.objects.create(
            label=label,
            prefix=prefix,
            hashed_secret=cls.hash_secret(secret),
            expires_at=expires_at,
        )
        return instance, f'{prefix}.{secret}'

    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < timezone.now():
            return False
        return True
