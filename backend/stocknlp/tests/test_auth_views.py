from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from stocknlp.auth_views import VerifyKeyView

factory = APIRequestFactory()


@override_settings(INTERVIEWER_ACCESS_KEY='super-secret')
class VerifyKeyViewTests(SimpleTestCase):
    def setUp(self):
        self.view = VerifyKeyView.as_view()

    def test_valid_header_key_returns_200(self):
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY='super-secret')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_valid_query_param_key_returns_200(self):
        request = factory.get('/api/auth/verify-key/', {'key': 'super-secret'})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_wrong_key_returns_403(self):
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY='wrong-key')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_missing_key_returns_403(self):
        request = factory.get('/api/auth/verify-key/')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    @override_settings(INTERVIEWER_ACCESS_KEY='')
    def test_no_configured_key_returns_403(self):
        request = factory.get('/api/auth/verify-key/', HTTP_X_ACCESS_KEY='anything')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
