from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User

from scraper.models import Content, Post, PostMeta, PostPrediction
from stocknlp.models import InterviewerKey
from tickers.models import Ticker
from signals.models import Signal
from signals.views.generation import SignalGenerationView
from signals.views.csv_views import ProcessCSVView, ProcessCSVJobStatusView
from signals.views.reporting import PredictionReportView
from signals.views.market_index import MarketOptimismIndexView


class SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

    def start(self):
        self.target(*self.args, **self.kwargs)


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
        mock_service.resolve_tickers.side_effect = RuntimeError("/etc/secret/db.conf leaked")

        request = self.factory.get('/api/signals/generate/', {
            'date': '2024-01-15',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.data['error'])
        self.assertEqual(response.data['error'], 'Signal generation failed')

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


@override_settings(RAW_DEBUG=False)
class SignalGenerationViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SignalGenerationView.as_view()

    def test_interviewer_key_alone_is_rejected_and_creates_no_signal(self):
        request = self.factory.get(
            '/api/signals/generate/',
            {'date': '2024-01-15', 'with_save': 'true'},
            HTTP_X_ACCESS_KEY='test-key',
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Signal.objects.count(), 0)

    def test_anonymous_alone_is_rejected_and_creates_no_signal(self):
        request = self.factory.get(
            '/api/signals/generate/', {'date': '2024-01-15', 'with_save': 'true'},
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Signal.objects.count(), 0)


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

    def test_oversized_file_returns_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        with override_settings(MAX_CSV_FILE_SIZE_BYTES=5):
            file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
            request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
            response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch('signals.views.csv_views.threading.Thread', SyncThread)
    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_successful_csv_processing(self, mock_get_dm, mock_csv_svc, *_):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_csv_svc.return_value.process.return_value = ({'$AAPL': {}}, [])

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)
        self.assertEqual(response.status_code, 202)
        self.assertIn('job_id', response.data)

        status_view = ProcessCSVJobStatusView.as_view()
        status_request = self.factory.get(f'/api/signals/process-csv/{response.data["job_id"]}/')
        status_response = status_view(status_request, job_id=response.data['job_id'])
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['status'], 'succeeded')
        self.assertEqual(status_response.data['results'], {'$AAPL': {}})

    @patch('signals.views.csv_views.threading.Thread', SyncThread)
    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_processing_failure_reflected_in_job_status(self, mock_get_dm, mock_csv_svc, *_):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_csv_svc.return_value.process.side_effect = ValueError('bad row')

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)

        status_view = ProcessCSVJobStatusView.as_view()
        status_request = self.factory.get(f'/api/signals/process-csv/{response.data["job_id"]}/')
        status_response = status_view(status_request, job_id=response.data['job_id'])
        self.assertEqual(status_response.data['status'], 'failed')
        self.assertEqual(status_response.data['error'], 'bad row')

    @patch('signals.views.csv_views.threading.Thread', SyncThread)
    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_unexpected_error_does_not_leak_exception_text(self, mock_get_dm, mock_csv_svc, *_):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_csv_svc.return_value.process.side_effect = RuntimeError("/etc/secret/db.conf leaked")

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)

        status_view = ProcessCSVJobStatusView.as_view()
        status_request = self.factory.get(f'/api/signals/process-csv/{response.data["job_id"]}/')
        status_response = status_view(status_request, job_id=response.data['job_id'])
        self.assertEqual(status_response.data['status'], 'failed')
        self.assertNotIn('secret', status_response.data['error'])
        self.assertEqual(status_response.data['error'], 'CSV processing failed')

    @patch('signals.views.csv_views.threading.Thread', SyncThread)
    @patch('signals.views.csv_views.CSVProcessingService')
    @patch('signals.views.csv_views.get_data_manager')
    def test_timeout_reflected_in_job_status(self, mock_get_dm, mock_csv_svc, *_):
        from signals.services.csv_service import CSVProcessingTimeout
        mock_get_dm.return_value = (MagicMock(), None)
        exc = CSVProcessingTimeout('too slow')
        exc.partial = ({'$AAPL': {}}, [{'details': 'partial'}])
        mock_csv_svc.return_value.process.side_effect = exc

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile('data.csv', b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n', content_type='text/csv')
        request = self.factory.post('/api/signals/process-csv/', {'file': file}, format='multipart')
        response = self.view(request)

        status_view = ProcessCSVJobStatusView.as_view()
        status_request = self.factory.get(f'/api/signals/process-csv/{response.data["job_id"]}/')
        status_response = status_view(status_request, job_id=response.data['job_id'])
        self.assertEqual(status_response.data['status'], 'timed_out')
        self.assertEqual(status_response.data['results'], {'$AAPL': {}})


class ProcessCSVJobStatusViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ProcessCSVJobStatusView.as_view()

    def test_unknown_job_id_returns_404(self):
        request = self.factory.get('/api/signals/process-csv/does-not-exist/')
        response = self.view(request, job_id='does-not-exist')
        self.assertEqual(response.status_code, 404)


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
    def test_internal_error_does_not_leak_exception_text(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.side_effect = RuntimeError("/etc/secret/db.conf leaked")

        request = self.factory.get('/api/signals/prediction-report/', {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.data['error'])
        self.assertEqual(response.data['error'], 'Report generation failed')

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


class MarketOptimismIndexViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = MarketOptimismIndexView.as_view()
        self.today = timezone.now().date()

    def _make_post(self, symbol, when, probabilities):
        ticker = Ticker.objects.create(symbol=symbol, type='stock', full_name=symbol)
        content = Content.objects.create(text=f'{symbol} post')
        meta = PostMeta.objects.create(likes=1)
        prediction = PostPrediction.objects.create(
            prediction=2, probabilities=probabilities, model_name='test',
        )
        return Post.objects.create(
            time_stamp=when,
            related_ticker=ticker,
            related_content=content,
            post_metadata=meta,
            post_prediction=prediction,
        )

    def test_invalid_start_date_returns_400(self):
        request = self.factory.get('/api/signals/market-index/', {'start_date': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_invalid_end_date_returns_400(self):
        request = self.factory.get('/api/signals/market-index/', {'end_date': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_start_after_end_returns_400(self):
        request = self.factory.get('/api/signals/market-index/', {
            'start_date': '2024-02-01',
            'end_date': '2024-01-01',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_days_with_no_posts_are_omitted(self):
        request = self.factory.get('/api/signals/market-index/', {
            'start_date': (self.today - timedelta(days=3)).isoformat(),
            'end_date': self.today.isoformat(),
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['series'], [])

    def test_pools_posts_across_tickers_into_one_daily_score(self):
        self._make_post('AAA', timezone.now(), [0.1, 0.2, 0.7])
        self._make_post('BBB', timezone.now(), [0.1, 0.2, 0.7])

        request = self.factory.get('/api/signals/market-index/', {
            'start_date': self.today.isoformat(),
            'end_date': self.today.isoformat(),
        })
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['series']), 1)
        self.assertEqual(response.data['series'][0]['tweet_count'], 2)

    def test_defaults_to_full_history_when_no_dates_given(self):
        self._make_post('AAA', timezone.now(), [0.1, 0.2, 0.7])

        request = self.factory.get('/api/signals/market-index/')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['series']), 1)

    @patch('signals.views.market_index.SignalService')
    def test_internal_error_does_not_leak_exception_text(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.get_all_posts_in_range.side_effect = RuntimeError("/etc/secret/db.conf leaked")

        request = self.factory.get('/api/signals/market-index/', {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.data['error'])
        self.assertEqual(response.data['error'], 'Market index generation failed')


@override_settings(RAW_DEBUG=False)
class MarketOptimismIndexViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = MarketOptimismIndexView.as_view()
        self.owner = User.objects.create_user(username='owner', password='pw123456')
        _, self.raw_key = InterviewerKey.create_key(label='test')

    def test_anonymous_no_key_denied(self):
        request = self.factory.get('/api/signals/market-index/')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_interviewer_key_allowed(self):
        request = self.factory.get('/api/signals/market-index/', HTTP_X_ACCESS_KEY=self.raw_key)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_owner_allowed(self):
        request = self.factory.get('/api/signals/market-index/')
        force_authenticate(request, user=self.owner)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
