from __future__ import annotations

import json
import uuid
from datetime import date

import redis
from django.apps import apps

redis_client = redis.StrictRedis()


def get_data_manager():
    return apps.get_app_config('scraper').DATA_MANAGER


def default_serializer(obj):
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    raise TypeError(f"Type {type(obj)} not serializable")


def enqueue_user_data(user_data):
    if 'request_id' not in user_data:
        user_data['request_id'] = str(uuid.uuid4())
    redis_client.rpush(
        'user_queue', json.dumps(
            user_data, default=default_serializer,
        ),
    )
    return user_data['request_id']


def enqueue_scraper_data(scraper_data):
    redis_client.rpush(
        'scraper_queue', json.dumps(
            scraper_data, default=default_serializer,
        ),
    )


def priority_worker():
    while True:
        try:
            data_manager = get_data_manager()
            raw_data = redis_client.lpop('user_queue')
            if raw_data:
                data = json.loads(raw_data)
                request_id = data['request_id']
                result = data_manager.eval_sentiment(data, with_save=False)
                redis_client.rpush(
                    f'response_queue:{request_id}', json.dumps(result),
                )
                continue

            raw_data = redis_client.lpop('scraper_queue')
            if raw_data:
                data = json.loads(raw_data)
                data_manager.eval_sentiment(data, with_save=True)
        except Exception as e:
            print(f"[ERROR] Failed to process data: {e}")
