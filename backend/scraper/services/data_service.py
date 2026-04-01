from __future__ import annotations

from datetime import timedelta
from django.apps import apps
from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError, APIException

PREDICTION_CLASSES = {0: 0, 1: 0, 2: 0}  # negative, neutral, positive


class DataService:
    def __init__(self):
        try:
            self.data_manager = apps.get_app_config('scraper').DATA_MANAGER
        except AttributeError:
            raise APIException("DataManager not initialized")

    def evaluate_sentiment(self, tweet_data: dict, with_save: bool = False):
        model_id = tweet_data.get('model_id')
        try:
            result = self.data_manager.eval_sentiment(
                {
                    'text': tweet_data['tweet'],
                    'ticker': tweet_data['ticker'],
                    'source_name': tweet_data.get('source_name', ''),
                    'date': tweet_data.get('date'),
                },
                with_save,
                model_id=model_id,
            )
            return result
        except ValueError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise APIException(f"Unexpected error during evaluation: {e}")

    def get_predictions_by_day(self, ticker_symbols: str | None = None, days: int = 30):
        from django.core.cache import cache

        cache_key = f"predictions:{ticker_symbols or 'all'}:{days}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        Post = apps.get_model('scraper', 'Post')
        Ticker = apps.get_model('tickers', 'Ticker')

        end_date = now().date()
        start_date = end_date - timedelta(days=days)

        query = Post.objects.filter(time_stamp__range=[start_date, end_date])

        if ticker_symbols and ticker_symbols != 'all':
            symbols = [s.strip() for s in ticker_symbols.split(',')]
            query = query.filter(related_ticker__symbol__in=symbols)
            active_tickers = Ticker.objects.filter(symbol__in=symbols)
        else:
            active_tickers = Ticker.objects.all()

        aggregations = (
            query.annotate(day=TruncDate('time_stamp'))
            .values('related_ticker__symbol', 'day', 'post_prediction__prediction')
            .annotate(count=Count('post_id'))
            .order_by('day')
        )

        results_map = {t.symbol: {} for t in active_tickers}

        for entry in aggregations:
            symbol = entry['related_ticker__symbol']
            date_str = entry['day'].isoformat()
            pred = entry['post_prediction__prediction']
            count = entry['count']

            if symbol not in results_map:
                continue

            if date_str not in results_map[symbol]:
                results_map[symbol][date_str] = dict(PREDICTION_CLASSES)

            day_data = results_map[symbol][date_str]
            day_data[pred] = count

        result = [
            {'ticker': symbol, 'predictions': predictions}
            for symbol, predictions in results_map.items()
        ]

        cache.set(cache_key, result, timeout=settings.CACHE_TTL_PREDICTIONS)
        return result
