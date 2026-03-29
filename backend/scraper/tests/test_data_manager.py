from unittest.mock import patch, MagicMock

from django.test import TestCase

from scraper.managers.data_manager.data_manager import DataManager


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

    def test_handles_prediction_failure_gracefully(self):
        self.mock_preprocessor.preprocess.return_value = MagicMock()
        self.mock_manager.predict.side_effect = RuntimeError('Model exploded')

        result = self.dm.eval_sentiment({'text': 'test', 'ticker': '$X'})
        self.assertEqual(result['prediction'], 'unknown')
        self.assertEqual(result['predicted_probabilities'], [])

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
