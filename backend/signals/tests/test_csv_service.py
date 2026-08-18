import io
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from signals.services.csv_service import CSVProcessingService


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
