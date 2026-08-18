import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from signals.models import UploadedFile

CSV_CONTENT = b'Date,Ticker,Tweet\n2024-01-01,AAPL,bullish\n2024-01-02,AAPL,bearish\n'


@override_settings(
    RAW_DEBUG=False,
    INTERVIEWER_ACCESS_KEY='test-key',
    MEDIA_ROOT=tempfile.mkdtemp(),
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class UploadedFileViewSetTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pw123456')

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.interviewer_client = APIClient()
        self.interviewer_headers = {'HTTP_X_ACCESS_KEY': 'test-key'}

        self.anon_client = APIClient()

        self.visible_file = UploadedFile.objects.create(
            display_name='visible.csv',
            file=SimpleUploadedFile('visible.csv', CSV_CONTENT),
            is_interviewer_visible=True,
        )
        self.hidden_file = UploadedFile.objects.create(
            display_name='hidden.csv',
            file=SimpleUploadedFile('hidden.csv', CSV_CONTENT),
            is_interviewer_visible=False,
        )

    def tearDown(self):
        for f in UploadedFile.objects.all():
            f.file.delete(save=False)

    def test_anonymous_list_denied(self):
        response = self.anon_client.get('/api/signals/files/')
        self.assertEqual(response.status_code, 403)

    def test_owner_list_returns_all_files(self):
        response = self.owner_client.get('/api/signals/files/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)

    def test_interviewer_list_returns_only_visible_files(self):
        response = self.interviewer_client.get('/api/signals/files/', **self.interviewer_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['file_id'], self.visible_file.file_id)

    def test_interviewer_create_denied(self):
        response = self.interviewer_client.post(
            '/api/signals/files/',
            {'display_name': 'new.csv', 'file': SimpleUploadedFile('new.csv', CSV_CONTENT)},
            format='multipart',
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_create_allowed(self):
        response = self.owner_client.post(
            '/api/signals/files/',
            {'display_name': 'new.csv', 'file': SimpleUploadedFile('new.csv', CSV_CONTENT)},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['row_count'], 2)
        self.assertEqual(UploadedFile.objects.count(), 3)

    @override_settings(MAX_CSV_ROWS=1)
    def test_owner_create_rejects_too_many_rows(self):
        response = self.owner_client.post(
            '/api/signals/files/',
            {'display_name': 'new.csv', 'file': SimpleUploadedFile('new.csv', CSV_CONTENT)},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(UploadedFile.objects.count(), 2)

    def test_interviewer_preview_hidden_file_returns_404(self):
        response = self.interviewer_client.get(
            f'/api/signals/files/{self.hidden_file.file_id}/preview/', **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_interviewer_preview_visible_file_returns_rows(self):
        response = self.interviewer_client.get(
            f'/api/signals/files/{self.visible_file.file_id}/preview/', **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['rows']), 2)

    def test_owner_preview_any_file(self):
        response = self.owner_client.get(f'/api/signals/files/{self.hidden_file.file_id}/preview/')
        self.assertEqual(response.status_code, 200)

    def test_interviewer_partial_update_denied(self):
        response = self.interviewer_client.patch(
            f'/api/signals/files/{self.visible_file.file_id}/',
            {'is_interviewer_visible': False}, format='json',
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_interviewer_destroy_denied(self):
        response = self.interviewer_client.delete(
            f'/api/signals/files/{self.visible_file.file_id}/', **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_partial_update_toggles_visibility(self):
        response = self.owner_client.patch(
            f'/api/signals/files/{self.hidden_file.file_id}/',
            {'is_interviewer_visible': True}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.hidden_file.refresh_from_db()
        self.assertTrue(self.hidden_file.is_interviewer_visible)

    @patch('signals.views.files.get_data_manager')
    @patch('signals.views.files.CSVProcessingService')
    def test_run_uses_cache_on_second_call(self, mock_service_cls, mock_get_dm):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_service_cls.return_value.process.return_value = ({'$AAPL': {}}, [])

        url = f'/api/signals/files/{self.visible_file.file_id}/run/'
        response1 = self.owner_client.get(url)
        response2 = self.owner_client.get(url)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        mock_service_cls.return_value.process.assert_called_once()

    @patch('signals.views.files.get_data_manager')
    @patch('signals.views.files.CSVProcessingService')
    def test_run_400_on_valueerror(self, mock_service_cls, mock_get_dm):
        mock_get_dm.return_value = (MagicMock(), None)
        mock_service_cls.return_value.process.side_effect = ValueError('bad file')

        response = self.owner_client.get(
            f'/api/signals/files/{self.visible_file.file_id}/run/',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'bad file')

    def test_interviewer_run_hidden_file_returns_404(self):
        response = self.interviewer_client.get(
            f'/api/signals/files/{self.hidden_file.file_id}/run/',
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_interviewer_run_visible_file_allowed(self):
        with patch('signals.views.files.get_data_manager', return_value=(MagicMock(), None)), \
             patch('signals.views.files.CSVProcessingService') as mock_service_cls:
            mock_service_cls.return_value.process.return_value = ({'$AAPL': {}}, [])
            response = self.interviewer_client.get(
                f'/api/signals/files/{self.visible_file.file_id}/run/',
                **self.interviewer_headers,
            )
        self.assertEqual(response.status_code, 200)
