from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import date

import redis
from django.apps import apps

logger = logging.getLogger(__name__)

# Lazily initialised so Django can import this module even if Redis is down
_redis_client = None


def get_redis() -> redis.StrictRedis:
    """Return a shared Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        from django.conf import settings
        host = getattr(settings, 'REDIS_HOST', 'localhost')
        port = int(getattr(settings, 'REDIS_PORT', 6379))
        _redis_client = redis.StrictRedis(host=host, port=port, db=0)
    return _redis_client


def get_data_manager():
    return apps.get_app_config('scraper').DATA_MANAGER


def _serialize(obj):
    """JSON serializer that handles date objects."""
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    raise TypeError(f"Type {type(obj)} not serializable")


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
    get_redis().rpush('user_queue', json.dumps(user_data, default=_serialize))
    return user_data['request_id']


def enqueue_scraper_data(scraper_data: dict) -> None:
    """Push a background scraper post to the low-priority scraper queue."""
    get_redis().rpush('scraper_queue', json.dumps(scraper_data, default=_serialize))


# ---------------------------------------------------------------------------
# Consumer  (run via: python manage.py run_llm_worker)
# ---------------------------------------------------------------------------

def priority_worker() -> None:
    """
    Single-threaded LLM worker:
      1. Always drain user_queue first (high priority).
      2. Only process scraper_queue when user_queue is empty.

    Uses blpop (blocking pop) so the process sleeps when both queues are
    empty instead of spinning at 100% CPU.
    Includes exponential backoff on repeated errors to protect against
    Redis outages or consistently broken payloads.
    """
    client = get_redis()
    backoff = 1  # seconds; doubles on each consecutive error, resets on success

    logger.info("LLM worker started. Listening on user_queue → scraper_queue …")

    while True:
        try:
            # blpop blocks until at least one queue has data.
            # Priority: user_queue is listed first — Redis checks left-to-right.
            result = client.blpop(['user_queue', 'scraper_queue'], timeout=5)

            if result is None:
                # timeout expired, nothing arrived — just loop again
                continue

            queue_name, raw = result
            data = json.loads(raw)
            data_manager = get_data_manager()

            if queue_name == b'user_queue':
                request_id = data['request_id']
                model_id = data.get('model_id')
                logger.debug("Processing user request %s (model=%s)", request_id, model_id)
                sentiment_result = data_manager.eval_sentiment(
                    data, with_save=False, model_id=model_id,
                )
                # Push result to a per-request response key with configurable TTL
                from django.conf import settings
                client.rpush(f'response_queue:{request_id}', json.dumps(sentiment_result))
                client.expire(f'response_queue:{request_id}', settings.CACHE_TTL_WORKER_RESULT)
            else:
                model_id = data.get('model_id')
                logger.debug("Processing scraper post for ticker %s (model=%s)", data.get('ticker'), model_id)
                data_manager.eval_sentiment(data, with_save=True, model_id=model_id)

            backoff = 1  # reset after a successful cycle

        except redis.RedisError as e:
            logger.error("Redis error: %s — retrying in %ss", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # cap at 60 s

        except Exception as e:
            logger.exception("Unexpected worker error: %s — retrying in %ss", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
