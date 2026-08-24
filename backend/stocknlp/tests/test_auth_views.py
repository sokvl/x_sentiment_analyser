from django.test import TestCase
from rest_framework.test import APIRequestFactory

from stocknlp.auth_views import VerifyKeyView
from stocknlp.models import InterviewerKey

factory = APIRequestFactory()


class VerifyKeyViewTests(TestCase):
    def setUp(self):
        self.view = VerifyKeyView.as_view()
        _, self.raw_key = InterviewerKey.create_key(label='test')

    def test_valid_header_key_returns_200(self):
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY=self.raw_key)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_valid_query_param_key_returns_200(self):
        request = factory.get('/api/auth/verify-key/', {'key': self.raw_key})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_wrong_key_returns_403(self):
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY='wrong-prefix.wrong-secret')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_missing_key_returns_403(self):
        request = factory.get('/api/auth/verify-key/')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_no_keys_configured_returns_403(self):
        InterviewerKey.objects.all().delete()
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY=self.raw_key)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
