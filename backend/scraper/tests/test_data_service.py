from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import ValidationError, APIException

from scraper.managers.data_manager.data_manager import ModelPredictionError
from scraper.services.data_service import DataService


class DataServiceEvaluateSentimentTests(TestCase):
    @patch('scraper.services.data_service.apps')
    def setUp(self, mock_apps):
        self.mock_data_manager = MagicMock()
        mock_apps.get_app_config.return_value.DATA_MANAGER = self.mock_data_manager
        self.service = DataService()

    def test_success_returns_data_manager_result(self):
        self.mock_data_manager.eval_sentiment.return_value = {
            'prediction': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
        }

        result = self.service.evaluate_sentiment(
            {'tweet': 'to the moon', 'ticker': '$AAPL'},
        )

        self.assertEqual(result['prediction'], 2)
        self.mock_data_manager.eval_sentiment.assert_called_once_with(
            {
                'text': 'to the moon',
                'ticker': '$AAPL',
                'source_name': '',
                'date': None,
            },
            False,
            model_id=None,
        )

    def test_value_error_from_data_manager_becomes_validation_error(self):
        self.mock_data_manager.eval_sentiment.side_effect = ValueError(
            "tweet_object must contain 'text' and 'ticker' keys.",
        )

        with self.assertRaises(ValidationError):
            self.service.evaluate_sentiment({'tweet': 'x', 'ticker': '$AAPL'})

    def test_nan_prediction_failure_raises_api_exception_not_validation_error(self):
        # A NaN slipping into the model (e.g. a bad tensor op) is caught inside
        # DataManager.eval_sentiment and re-raised as ModelPredictionError, which
        # is *not* a ValueError. DataService's blanket `except Exception` catches
        # it and turns it into a 500 APIException, never a 400 ValidationError,
        # regardless of the underlying NaN-related message.
        self.mock_data_manager.eval_sentiment.side_effect = ModelPredictionError()

        with self.assertRaises(APIException) as ctx:
            self.service.evaluate_sentiment({'tweet': 'x', 'ticker': '$AAPL'})

        self.assertNotIsInstance(ctx.exception, ValidationError)
        self.assertEqual(ctx.exception.status_code, 500)

    def test_nan_valueerror_raised_directly_by_data_manager_still_becomes_validation_error(self):
        # If a NaN-related ValueError were ever raised *outside* the predict
        # try/except in DataManager (unlike today), DataService would instead
        # treat it as a 400 client error and swallow the real cause.
        self.mock_data_manager.eval_sentiment.side_effect = ValueError(
            'cannot convert float NaN to integer',
        )

        with self.assertRaises(ValidationError) as ctx:
            self.service.evaluate_sentiment({'tweet': 'x', 'ticker': '$AAPL'})

        self.assertIn('NaN', str(ctx.exception.detail))
