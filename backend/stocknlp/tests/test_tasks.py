import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from scraper.managers.data_manager.data_manager import ModelPredictionError
from stocknlp import tasks


class EnqueueUserDataTests(TestCase):
    @patch('stocknlp.tasks.django_rq')
    def test_generates_request_id_and_enqueues_with_retry(self, mock_django_rq):
        mock_queue = MagicMock()
        mock_django_rq.get_queue.return_value = mock_queue

        data = {'text': 'bullish', 'ticker': '$AAPL'}
        request_id = tasks.enqueue_user_data(data)

        self.assertEqual(data['request_id'], request_id)
        mock_django_rq.get_queue.assert_called_once_with('user_queue')
        args, kwargs = mock_queue.enqueue.call_args
        self.assertEqual(args[0], tasks.process_user_job)
        self.assertEqual(args[1], data)
        self.assertEqual(kwargs['retry'].max, 3)
        self.assertEqual(kwargs['retry'].intervals, [10, 30, 90])

    @patch('stocknlp.tasks.django_rq')
    def test_preserves_existing_request_id(self, mock_django_rq):
        mock_django_rq.get_queue.return_value = MagicMock()
        data = {'text': 'x', 'ticker': '$AAPL', 'request_id': 'already-set'}
        request_id = tasks.enqueue_user_data(data)
        self.assertEqual(request_id, 'already-set')


class EnqueueScraperDataTests(TestCase):
    @patch('stocknlp.tasks.django_rq')
    def test_enqueues_with_retry_no_request_id(self, mock_django_rq):
        mock_queue = MagicMock()
        mock_django_rq.get_queue.return_value = mock_queue

        data = {'text': 'x', 'ticker': '$AAPL'}
        result = tasks.enqueue_scraper_data(data)

        self.assertIsNone(result)
        self.assertNotIn('request_id', data)
        mock_django_rq.get_queue.assert_called_once_with('scraper_queue')
        args, kwargs = mock_queue.enqueue.call_args
        self.assertEqual(args[0], tasks.process_scraper_job)
        self.assertEqual(args[1], data)
        self.assertEqual(kwargs['retry'].max, 3)


class ProcessUserJobTests(TestCase):
    def setUp(self):
        self.data = {'text': 'bullish', 'ticker': '$AAPL', 'request_id': 'req-1'}

    @patch('stocknlp.tasks.apps')
    def test_success_writes_response_queue(self, mock_apps):
        mock_dm = MagicMock()
        mock_dm.eval_sentiment.return_value = {'predicted_probabilities': [0.1, 0.2, 0.7]}
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        with patch('stocknlp.tasks.get_redis') as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client
            tasks.process_user_job(self.data)

        mock_dm.eval_sentiment.assert_called_once_with(self.data, with_save=False, model_id=None)
        mock_client.rpush.assert_called_once()
        key, payload = mock_client.rpush.call_args[0]
        self.assertEqual(key, 'response_queue:req-1')
        self.assertEqual(json.loads(payload), {'predicted_probabilities': [0.1, 0.2, 0.7]})
        mock_client.expire.assert_called_once()

    @patch('stocknlp.tasks.apps')
    def test_malformed_payload_dead_lettered_not_raised(self, mock_apps):
        mock_dm = MagicMock()
        mock_dm.eval_sentiment.side_effect = ValueError("tweet_object must contain 'text' and 'ticker' keys.")
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        with patch('stocknlp.tasks._dead_letter') as mock_dead_letter, \
             patch('stocknlp.tasks.get_redis') as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client
            tasks.process_user_job(self.data)

        mock_dead_letter.assert_called_once()
        self.assertEqual(mock_dead_letter.call_args[0][0], 'user_queue')
        self.assertEqual(mock_dead_letter.call_args[0][1], self.data)
        mock_client.rpush.assert_not_called()

    @patch('stocknlp.tasks.apps')
    def test_unexpected_error_propagates_for_rq_retry(self, mock_apps):
        mock_dm = MagicMock()
        mock_dm.eval_sentiment.side_effect = ModelPredictionError('model exploded')
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        with self.assertRaises(ModelPredictionError):
            tasks.process_user_job(self.data)


class ProcessScraperJobTests(TestCase):
    def setUp(self):
        self.data = {'text': 'bullish', 'ticker': '$AAPL'}

    @patch('stocknlp.tasks.apps')
    def test_success_calls_eval_sentiment_with_save(self, mock_apps):
        mock_dm = MagicMock()
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        tasks.process_scraper_job(self.data)

        mock_dm.eval_sentiment.assert_called_once_with(self.data, with_save=True, model_id=None)

    @patch('stocknlp.tasks.apps')
    def test_malformed_payload_dead_lettered_not_raised(self, mock_apps):
        mock_dm = MagicMock()
        mock_dm.eval_sentiment.side_effect = ValueError('bad payload')
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        with patch('stocknlp.tasks._dead_letter') as mock_dead_letter:
            tasks.process_scraper_job(self.data)

        mock_dead_letter.assert_called_once_with('scraper_queue', self.data, 'bad payload')

    @patch('stocknlp.tasks.apps')
    def test_unexpected_error_propagates_for_rq_retry(self, mock_apps):
        mock_dm = MagicMock()
        mock_dm.eval_sentiment.side_effect = ModelPredictionError('model exploded')
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm

        with self.assertRaises(ModelPredictionError):
            tasks.process_scraper_job(self.data)


class DeadLetterTests(TestCase):
    def test_pushes_structured_entry(self):
        with patch('stocknlp.tasks.get_redis') as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client
            tasks._dead_letter('user_queue', {'ticker': 'AAPL'}, 'missing text')

        mock_client.rpush.assert_called_once()
        key, payload = mock_client.rpush.call_args[0]
        self.assertEqual(key, 'dead_letter_queue')
        entry = json.loads(payload)
        self.assertEqual(entry['queue'], 'user_queue')
        self.assertEqual(entry['payload'], {'ticker': 'AAPL'})
        self.assertEqual(entry['reason'], 'missing text')
        self.assertIn('failed_at', entry)
