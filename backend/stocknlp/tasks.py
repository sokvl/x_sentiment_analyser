from __future__ import annotations

import functools
import json
import logging
import uuid
from datetime import date

import django_rq
import redis
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from rq import Retry

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_redis() -> redis.StrictRedis:
    """Return a shared Redis client, created once on first call."""
    host = getattr(settings, 'REDIS_HOST', 'localhost')
    port = int(getattr(settings, 'REDIS_PORT', 6379))
    return redis.StrictRedis(host=host, port=port, db=0)


def _serialize(obj):
    """JSON serializer that handles date objects."""
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    raise TypeError(f"Type {type(obj)} not serializable")


def _retry_policy() -> Retry:
    return Retry(max=settings.WORKER_JOB_MAX_RETRIES, interval=settings.WORKER_JOB_RETRY_INTERVALS)


def _dead_letter(queue_name: str, payload: dict, reason: str) -> None:
    get_redis().rpush('dead_letter_queue', json.dumps({
        'queue': queue_name,
        'payload': payload,
        'reason': reason,
        'failed_at': timezone.now().isoformat(),
    }, default=_serialize))


# ---------------------------------------------------------------------------
# Producers  (called by scrapers / views)
# ---------------------------------------------------------------------------

def enqueue_user_data(user_data: dict) -> str:
    """
    Push an on-demand evaluation request to the high-priority user queue.
    Returns the request_id so the caller can poll for the result.
    """
    if 'request_id' not in user_data:
        user_data['request_id'] = str(uuid.uuid4())
    django_rq.get_queue('user_queue').enqueue(
        process_user_job, user_data, retry=_retry_policy(),
    )
    return user_data['request_id']


def enqueue_scraper_data(scraper_data: dict) -> None:
    """Push a background scraper post to the low-priority scraper queue."""
    django_rq.get_queue('scraper_queue').enqueue(
        process_scraper_job, scraper_data, retry=_retry_policy(),
    )


# ---------------------------------------------------------------------------
# Jobs  (run by: python manage.py run_llm_worker)
# ---------------------------------------------------------------------------

def process_user_job(data: dict) -> None:
    request_id = data['request_id']
    model_id = data.get('model_id')
    data_manager = apps.get_app_config('scraper').DATA_MANAGER

    try:
        result = data_manager.eval_sentiment(data, with_save=False, model_id=model_id)
    except ValueError as e:
        logger.warning('Malformed user job payload, sending to dead letter: %s', e)
        _dead_letter('user_queue', data, str(e))
        return

    client = get_redis()
    client.rpush(f'response_queue:{request_id}', json.dumps(result, default=_serialize))
    client.expire(f'response_queue:{request_id}', settings.CACHE_TTL_WORKER_RESULT)


def process_scraper_job(data: dict) -> None:
    model_id = data.get('model_id')
    data_manager = apps.get_app_config('scraper').DATA_MANAGER

    try:
        data_manager.eval_sentiment(data, with_save=True, model_id=model_id)
    except ValueError as e:
        logger.warning('Malformed scraper job payload, sending to dead letter: %s', e)
        _dead_letter('scraper_queue', data, str(e))
