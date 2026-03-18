"""
Cache invalidation signals for the scraper app.

When a Config object is saved or deleted, we clear the active config cache
so the frontend always sees fresh configuration without a stale TTL wait.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


@receiver(post_save, sender='scraper.Config')
@receiver(post_delete, sender='scraper.Config')
def invalidate_config_cache(sender, instance, **kwargs):
    """Clear all config-related cache keys when a Config is modified."""
    cache.delete_pattern('*config*')
