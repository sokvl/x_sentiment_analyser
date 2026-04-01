from __future__ import annotations

import json
import logging

from django.apps import apps
from django.conf import settings
from django.db import DatabaseError, transaction

logger = logging.getLogger(__name__)


class DataManager:
    """
    Evaluates sentiment for tweets using the model specified at call time.

    The actual model selection is delegated to the ModelRegistry, which
    lazily loads and caches ModelManager/preprocessor pairs.  This class
    only needs a reference to the registry and the default model ID
    (used when callers don't specify one).
    """

    def __init__(self, model_registry, default_model_id: str):
        self.registry = model_registry
        self.default_model_id = default_model_id
        self._ticker_to_index: dict | None = None

    @staticmethod
    def _load_json(path: str) -> dict:
        with open(path, encoding='utf-8') as file:
            return json.load(file)

    def _get_ticker_to_index(self) -> dict:
        if self._ticker_to_index is None:
            self._ticker_to_index = self._load_json(settings.TICKER_TO_INDEX_PATH)
        return self._ticker_to_index

    def eval_sentiment(
        self,
        tweet_object: dict,
        with_save: bool = False,
        model_id: str | None = None,
    ) -> dict:
        if 'text' not in tweet_object or 'ticker' not in tweet_object:
            raise ValueError(
                "tweet_object must contain 'text' and 'ticker' keys.",
            )

        model_id = model_id or self.default_model_id
        model_manager, preprocessor, model_type = self.registry.get(model_id)

        tweet = tweet_object['text']
        ticker = tweet_object['ticker']
        cleaned_text = preprocessor.clean(tweet)
        processed_input = preprocessor.preprocess(tweet)

        try:
            if model_type == 'lstmcnn_model':
                ticker_index = self._get_ticker_to_index().get(ticker, 0)
                prediction = model_manager.predict(
                    processed_input,
                    [ticker_index],
                )
            elif model_type == 'transformer_model':
                prediction = model_manager.predict(processed_input, None)
            else:
                raise ValueError(f'Unsupported model type: {model_type}')
        except Exception:
            logger.exception('Prediction failed for model %s', model_id)
            prediction = {
                'predicted_sentiment': 'unknown',
                'predicted_probabilities': [],
            }

        tweet_data = {
            **tweet_object,
            'cleaned_text': cleaned_text,
            'prediction': prediction.get('predicted_sentiment'),
            'predicted_probabilities': prediction.get('predicted_probabilities'),
        }

        if with_save:
            self.process_and_save_post(tweet_data, model_manager)

        return tweet_data

    def process_and_save_post(self, data: dict, model_manager=None):
        Post = apps.get_model('scraper', 'Post')
        PostMeta = apps.get_model('scraper', 'PostMeta')
        Ticker = apps.get_model('tickers', 'Ticker')
        Content = apps.get_model('scraper', 'Content')
        Source = apps.get_model('scraper', 'Source')
        PostPrediction = apps.get_model('scraper', 'PostPrediction')

        if model_manager is None:
            model_manager, _, _ = self.registry.get(self.default_model_id)

        try:
            with transaction.atomic():
                symbol = data['ticker']
                ticker, _ = Ticker.objects.get_or_create(
                    symbol=symbol,
                    defaults={'full_name': symbol, 'type': 'stock'},
                )
                content, _ = Content.objects.get_or_create(text=data['text'])
                source, _ = Source.objects.get_or_create(name=data['source'])
                post_meta, _ = PostMeta.objects.get_or_create(
                    source=source,
                    likes=data.get('likes'),
                    shares=data.get('retweets'),
                    views=data.get('views'),
                    comments=data.get('replies'),
                )
                post_prediction, _ = PostPrediction.objects.get_or_create(
                    prediction=data['prediction'],
                    probabilities=data['predicted_probabilities'],
                    model_name=model_manager.get_model_name(),
                )
                post, created = Post.objects.get_or_create(
                    time_stamp=data['date'],
                    related_ticker=ticker,
                    related_content=content,
                    defaults={
                        'post_metadata': post_meta,
                        'post_prediction': post_prediction,
                    },
                )
            if created:
                logger.info('New post saved: %s', post)
            else:
                logger.debug('Post already exists: %s', post)
        except DatabaseError:
            logger.exception('Database error occurred while saving data')
        except Exception:
            logger.exception('Unexpected error while saving data')
            raise
