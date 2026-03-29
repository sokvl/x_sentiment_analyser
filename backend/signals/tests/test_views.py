from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from signals.views.generation import SignalGenerationView
from signals.views.csv_views import ProcessCSVView
from signals.views.reporting import PredictionReportView


class SignalGenerationViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SignalGenerationView.as_view()

    def test_missing_date_returns_400(self):
        request = self.factory.get('/api/signals/generate/')
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_invalid_date_returns_400(self):
        request = self.factory.get('/api/signals/generate/', {'date': 'bad-date'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch('signals.views.generation.SignalService')
    def test_successful_generation(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = [MagicMock(symbol='AAPL')]
        mock_service.generate_for_tickers.return_value = {
            'AAPL': {'signal_type': 'BUY', 'confidence_score': 0.5}
        }

        request = self.factory.get('/api/signals/generate/', {
            'date': '2024-01-15',
            'tickers': 'AAPL',
            'config_id': '1',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('AAPL', response.data)

    @patch('signals.views.generation.SignalService')
    def test_ticker_not_found_returns_404(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.side_effect = ValueError("No tickers found")

        request = self.factory.get('/api/signals/generate/', {
            'date': '2024-01-15',
            'tickers': 'UNKNOWN',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 404)

    @patch('signals.views.generation.SignalService')
    def test_internal_error_returns_500(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.side_effect = RuntimeError("Unexpected")

        request = self.factory.get('/api/signals/generate/', {
            'date': '2024-01-15',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 500)

    @patch('signals.views.generation.SignalService')
    def test_defaults_to_all_tickers_and_lstmcnnv1(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = []
        mock_service.generate_for_tickers.return_value = {}

        request = self.factory.get('/api/signals/generate/', {'date': '2024-01-15'})
        self.view(request)
        mock_service.resolve_tickers.assert_called_once_with('all')
        call_kwargs = mock_service.generate_for_tickers.call_args
        self.assertEqual(call_kwargs.kwargs['used_model'], 'LSTMCNNv1')


class ProcessCSVViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ProcessCSVView.as_view()

    def test_no_file_returns_400(self):
        request = self.factory.post('/api/signals/process-csv/')
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_non_csv_file_returns_400(self):
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.txt', b'hello', content_type='text/plain')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_data_manager_not_initialized_returns_500(self, mock_get_dm, mock_csv_svc):
        mock_get_dm.return_value = (None, 'Not initialized')
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)
        self.assertEqual(response.status_code, 500)

    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_successful_csv_processing(self, mock_get_dm, mock_csv_svc):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_csv_svc.return_value.process.return_value = ({'$AAPL': {}}, [])

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertIn('errors', response.data)


class PredictionReportViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictionReportView.as_view()

    def test_missing_dates_returns_400(self):
        request = self.factory.get('/api/signals/prediction-report/')
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_missing_end_date_returns_400(self):
        request = self.factory.get('/api/signals/prediction-report/', {'start_date': '2024-01-01'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_invalid_date_format_returns_400(self):
        request = self.factory.get('/api/signals/prediction-report/', {
            'start_date': 'bad',
            'end_date': '2024-01-31',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_start_after_end_returns_400(self):
        request = self.factory.get('/api/signals/prediction-report/', {
            'start_date': '2024-02-01',
            'end_date': '2024-01-01',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch('signals.views.reporting.SignalService')
    def test_successful_report(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = []
        # Mock _generate_report via the view instance
        with patch.object(PredictionReportView, '_generate_report', return_value={'overall_accuracy': '50.0%'}):
            request = self.factory.get('/api/signals/prediction-report/', {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
            })
            response = self.view(request)
            self.assertEqual(response.status_code, 200)
