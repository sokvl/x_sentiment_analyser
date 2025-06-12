from __future__ import annotations

import json
import logging

from django.apps import apps
from django.conf import settings
from transformers import AutoTokenizer

from .model_processors import get_preprocessor

# from types import Dict


class DataManager:
    def __init__(self, model_bundle: dict):
        self.model_type = model_bundle['model_type']
        self.model_params = model_bundle['model_params']
        if model_bundle['model_type'] == 'lstmcnn_model':
            # TO DO LATER WE HAVE TO ADD FULL SUPPORT
            self.word_to_index = self._load_json(settings.WORD_TO_INDEX_PATH)
            self.max_len = 30
            self.pad_token = 0
            self.preprocessor = get_preprocessor(
                self.model_type,
                word_to_index=self.word_to_index,
                max_len=self.max_len,
                pad_token=self.pad_token,
            )
            # Load ticker vocabulary for ticker encoding
            self.ticker_to_index = self._load_json(
                settings.TICKER_TO_INDEX_PATH,
            )
        elif self.model_type == 'transformer_model':
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_params['weights_path'],
            )
            self.preprocessor = get_preprocessor(
                self.model_type,
                tokenizer=tokenizer,
            )
            logging.getLogger(__name__).debug(
                'Tokenizer loaded: %s', tokenizer,
            )
        else:
            raise ValueError('Unknown model type')

        cfg = apps.get_app_config('scraper')
        self.logger = logging.getLogger(__name__)
        self.model_manager = cfg.LSTM_MODEL_MANAGER

    def _load_json(self, path: str) -> dict:
        with open(path, encoding='utf-8') as file:
            return json.load(file)

    def eval_sentiment(self, tweet_object: dict, with_save: bool = False) -> dict:
        if 'text' not in tweet_object or 'ticker' not in tweet_object:
            raise ValueError(
                "tweet_object must contain 'text' and 'ticker' keys.",
            )

        tweet = tweet_object['text']
        ticker = tweet_object['ticker']
        processed_input = self.preprocessor.preprocess(tweet)

        try:
            if self.model_type == 'lstmcnn_model':
                ticker_index = self.ticker_to_index.get(
                    ticker, 0,
                )  # 0 for unknown ticker
                prediction = self.model_manager.predict(
                    processed_input,
                    [ticker_index],
                )
            elif self.model_type == 'transformer_model':
                prediction = self.model_manager.predict(processed_input, None)
            else:
                raise ValueError('Unsupported model type')
        except Exception:
            self.logger.exception('Prediction failed')
            prediction = {
                'predicted_sentiment': 'unknown',
                'predicted_probabilities': [],
            }

        tweet_data = {
            'text': tweet,
            'ticker': ticker,
            'processed_text': tweet,
            'source': tweet_object.get('source_name', ''),
            'date': tweet_object.get('date', ''),
            'prediction': prediction.get('predicted_sentiment'),
            'predicted_probabilities': prediction.get('predicted_probabilities'),
        }

        if with_save:
            self.process_and_save_post(tweet_data)

        return tweet_data

    def process_and_save_post(self, data: dict):
        Post = apps.get_model('scraper', 'Post')
        PostMeta = apps.get_model('scraper', 'PostMeta')
        Ticker = apps.get_model('tickers', 'Ticker')
        Content = apps.get_model('scraper', 'Content')
        Source = apps.get_model('scraper', 'Source')
        PostPrediction = apps.get_model('scraper', 'PostPrediction')
        try:
            ticker, _ = Ticker.objects.get_or_create(symbol=data['ticker'])
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
                model_name=self.model_manager.get_modelname(),
            )
            post, created = Post.objects.get_or_create(
                time_stamp=data['date'],
                related_ticker=ticker,
                related_content=content,
                post_metadata=post_meta,
                post_prediction=post_prediction,
            )
            if created:
                self.logger.info('New post saved: %s', post)
            else:
                self.logger.debug(
                    'Post already exists: %s',
                    post,
                )
        except Exception:
            self.logger.exception('Failed to save data')
