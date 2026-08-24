from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from django.db import DatabaseError
from django.test import TestCase

from scraper.managers.data_manager.data_manager import DataManager, ModelPredictionError
from scraper.models import NewsPost


class DataManagerEvalSentimentTests(TestCase):
    def setUp(self):
        self.mock_registry = MagicMock()
        self.mock_manager = MagicMock()
        self.mock_preprocessor = MagicMock()

        self.mock_registry.get.return_value = (
            self.mock_manager,
            self.mock_preprocessor,
            'transformer_model',
        )

        self.dm = DataManager(
            model_registry=self.mock_registry,
            default_model_id='FinBERT',
        )

    def test_raises_when_missing_text(self):
        with self.assertRaises(ValueError):
            self.dm.eval_sentiment({'ticker': '$AAPL'})

    def test_raises_when_missing_ticker(self):
        with self.assertRaises(ValueError):
            self.dm.eval_sentiment({'text': 'hello'})

    def test_uses_default_model_when_none_specified(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
        }

        self.dm.eval_sentiment({'text': 'bullish', 'ticker': '$AAPL'})
        self.mock_registry.get.assert_called_once_with('FinBERT')

    def test_uses_specified_model_id(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 0,
            'predicted_probabilities': [0.8, 0.1, 0.1],
        }

        self.dm.eval_sentiment(
            {'text': 'bearish', 'ticker': '$TSLA'},
            model_id='TweetBERT',
        )
        self.mock_registry.get.assert_called_once_with('TweetBERT')

    def test_returns_prediction_in_result(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 2,
            'predicted_probabilities': [0.05, 0.15, 0.80],
        }

        result = self.dm.eval_sentiment({'text': 'moon', 'ticker': '$AAPL'})
        self.assertEqual(result['prediction'], 2)
        self.assertEqual(result['predicted_probabilities'], [0.05, 0.15, 0.80])
        self.assertEqual(result['text'], 'moon')
        self.assertEqual(result['ticker'], '$AAPL')

    def test_prediction_failure_raises_model_prediction_error(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.side_effect = RuntimeError('Model exploded')

        with self.assertRaises(ModelPredictionError):
            self.dm.eval_sentiment({'text': 'test', 'ticker': '$X'})

    def test_nan_producing_prediction_raises_model_prediction_error(self):
        # e.g. a NaN slipping into a tensor op raises ValueError('cannot convert
        # float NaN to integer') deep inside model_manager.predict.
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.side_effect = ValueError(
            'cannot convert float NaN to integer',
        )

        with self.assertRaises(ModelPredictionError):
            self.dm.eval_sentiment({'text': 'test', 'ticker': '$X'})

    def test_transformer_model_passes_none_ticker(self):
        self.mock_preprocessor.preprocess.return_value = 'preprocessed'
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 1,
            'predicted_probabilities': [0.3, 0.4, 0.3],
        }

        self.dm.eval_sentiment({'text': 'neutral', 'ticker': '$MSFT'})
        self.mock_manager.predict.assert_called_once_with('preprocessed', None)

    def test_lstmcnn_model_passes_ticker_index(self):
        self.mock_registry.get.return_value = (
            self.mock_manager,
            self.mock_preprocessor,
            'lstmcnn_model',
        )
        self.mock_preprocessor.preprocess.return_value = [1, 2, 3]
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 0,
            'predicted_probabilities': [0.7, 0.2, 0.1],
        }

        with patch.object(DataManager, '_load_json', return_value={'$AAPL': 2}):
            self.dm.eval_sentiment(
                {'text': 'test', 'ticker': '$AAPL'},
                model_id='LSTMCNNv1',
            )
            self.mock_manager.predict.assert_called_once_with([1, 2, 3], [2])

    def test_with_save_calls_process_and_save(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
        }

        with patch.object(DataManager, 'process_and_save_post') as mock_save:
            self.dm.eval_sentiment(
                {'text': 'buy', 'ticker': '$AAPL'},
                with_save=True,
            )
            mock_save.assert_called_once()

    def test_without_save_does_not_call_process_and_save(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.return_value = {
            'predicted_sentiment': 1,
            'predicted_probabilities': [0.3, 0.4, 0.3],
        }

        with patch.object(DataManager, 'process_and_save_post') as mock_save:
            self.dm.eval_sentiment(
                {'text': 'hold', 'ticker': '$AAPL'},
                with_save=False,
            )
            mock_save.assert_not_called()


class SaveNewsPostTests(TestCase):
    def setUp(self):
        self.mock_registry = MagicMock()
        self.mock_manager = MagicMock()
        self.mock_manager.get_model_name.return_value = 'FinBERT'
        self.dm = DataManager(model_registry=self.mock_registry, default_model_id='FinBERT')

    def _base_data(self, **overrides):
        data = {
            'ticker': 'AAPL',
            'prediction': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
            'text': 'Apple headline. Apple summary.',
            'headline': 'Apple headline',
            'summary': 'Apple summary',
            'url': 'https://example.com/article',
            'publisher': 'TheStreet',
            'news_category': 'company news',
            'external_id': '25341',
            'published_at': datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        }
        data.update(overrides)
        return data

    def test_saves_news_post(self):
        self.dm.save_news_post(self._base_data(), model_manager=self.mock_manager)
        news_post = NewsPost.objects.get(external_id='25341')
        self.assertEqual(news_post.headline, 'Apple headline')
        self.assertEqual(news_post.ticker.symbol, 'AAPL')
        self.assertEqual(news_post.news_prediction.prediction, 2)
        self.assertEqual(news_post.news_prediction.model_name, 'FinBERT')

    def test_duplicate_external_id_does_not_raise(self):
        self.dm.save_news_post(self._base_data(), model_manager=self.mock_manager)
        self.dm.save_news_post(self._base_data(), model_manager=self.mock_manager)
        self.assertEqual(NewsPost.objects.filter(external_id='25341').count(), 1)

    def test_missing_optional_fields_still_saves(self):
        data = self._base_data()
        for key in ('summary', 'url', 'publisher', 'news_category'):
            del data[key]
        self.dm.save_news_post(data, model_manager=self.mock_manager)
        news_post = NewsPost.objects.get(external_id='25341')
        self.assertEqual(news_post.summary, '')
        self.assertEqual(news_post.url, '')

    @patch('scraper.managers.data_manager.data_manager.apps')
    def test_database_error_is_swallowed(self, mock_apps):
        from tickers.models import Ticker as RealTicker
        from scraper.models import PostPrediction as RealPostPrediction

        mock_news_post_model = MagicMock()
        mock_news_post_model.objects.get_or_create.side_effect = DatabaseError('boom')

        def get_model(app_label, model_name):
            return {
                'NewsPost': mock_news_post_model,
                'Ticker': RealTicker,
                'PostPrediction': RealPostPrediction,
            }[model_name]

        mock_apps.get_model.side_effect = get_model
        self.dm.save_news_post(self._base_data(), model_manager=self.mock_manager)

    @patch('scraper.managers.data_manager.data_manager.apps')
    def test_unexpected_error_is_reraised(self, mock_apps):
        mock_apps.get_model.side_effect = RuntimeError('boom')
        with self.assertRaises(RuntimeError):
            self.dm.save_news_post(self._base_data(), model_manager=self.mock_manager)
