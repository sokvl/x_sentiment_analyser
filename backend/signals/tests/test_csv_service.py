import io
import json
import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from signals.services.csv_service import CSVProcessingService, CSVProcessingTimeout


def make_csv_file(content: str, size: int | None = None):
    file_obj = io.BytesIO(content.encode('utf-8'))
    file_obj.size = size if size is not None else len(content.encode('utf-8'))
    return file_obj


@override_settings(MAX_CSV_FILE_SIZE_BYTES=100, MAX_CSV_ROWS=2)
class CSVProcessingServiceCapTests(TestCase):
    def setUp(self):
        self.service = CSVProcessingService()

    def test_oversized_file_raises_valueerror(self):
        file_obj = make_csv_file('Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', size=1000)
        with self.assertRaises(ValueError):
            self.service.process(file_obj)

    def test_too_many_rows_raises_valueerror(self):
        content = 'Date,Ticker,Tweet\n' + '2024-01-01,AAPL,bullish\n' * 5
        file_obj = make_csv_file(content)
        with self.assertRaises(ValueError):
            self.service.process(file_obj)

    @patch('signals.services.csv_service.fetch_historical_data')
    @patch('signals.services.csv_service.get_redis')
    @patch('signals.services.csv_service.enqueue_user_data')
    def test_within_limits_proceeds(self, mock_enqueue, mock_get_redis, mock_fetch_hist):
        mock_enqueue.return_value = 'req-1'
        mock_redis = MagicMock()
        mock_redis.brpop.return_value = (
            'response_queue:req-1',
            json.dumps({'predicted_probabilities': [0.1, 0.2, 0.7]}),
        )
        mock_get_redis.return_value = mock_redis
        mock_fetch_hist.return_value = None

        service = CSVProcessingService()
        file_obj = make_csv_file('Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n')
        results, errors = service.process(file_obj)

        self.assertEqual(errors, [])
        self.assertIn('$AAPL', results)


@override_settings(MAX_CSV_FILE_SIZE_BYTES=10_000_000, MAX_CSV_ROWS=100)
class CSVProcessingServiceParallelCollectTests(TestCase):
    @patch('signals.services.csv_service.fetch_historical_data')
    @patch('signals.services.csv_service.get_redis')
    @patch('signals.services.csv_service.enqueue_user_data')
    def test_all_rows_collected_regardless_of_completion_order(
        self, mock_enqueue, mock_get_redis, mock_fetch_hist,
    ):
        mock_fetch_hist.return_value = None
        counter = iter(range(5))
        mock_enqueue.side_effect = lambda data: f'req-{next(counter)}'

        mock_redis = MagicMock()
        mock_redis.brpop.side_effect = lambda key, timeout: (
            key, json.dumps({'predicted_probabilities': [0.1, 0.2, 0.7]}),
        )
        mock_get_redis.return_value = mock_redis

        content = 'Date,Ticker,Tweet\n' + ''.join(
            f'2024-01-0{i + 1},AAPL,tweet {i}\n' for i in range(5)
        )
        service = CSVProcessingService()
        results, errors = service.process(make_csv_file(content))

        self.assertEqual(errors, [])
        self.assertEqual(len(results['$AAPL']), 5)
        self.assertEqual(mock_redis.brpop.call_count, 5)


@override_settings(MAX_CSV_FILE_SIZE_BYTES=10_000_000, MAX_CSV_ROWS=100)
class CSVProcessingServiceDeadlineTests(TestCase):
    @patch('signals.services.csv_service.CSV_BATCH_SIZE', 1)
    def test_deadline_exceeded_raises_timeout_with_partial_results(self):
        content = 'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n2024-01-02,AAPL,bearish\n'
        service = CSVProcessingService()
        past_deadline = time.monotonic() - 1

        with self.assertRaises(CSVProcessingTimeout) as ctx:
            service.process(make_csv_file(content), deadline=past_deadline)

        partial_results, partial_errors = ctx.exception.partial
        self.assertEqual(partial_results, {})
        self.assertEqual(partial_errors, [])
