from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from stocknlp.health_views import HealthCheckView

factory = APIRequestFactory()


class HealthCheckViewTests(TestCase):
    def setUp(self):
        self.view = HealthCheckView.as_view()

    def test_healthy_when_db_and_redis_ok(self):
        with patch.object(HealthCheckView, '_check_db', return_value=True), \
             patch.object(HealthCheckView, '_check_redis', return_value=True):
            request = factory.get('/api/health/')
            response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['checks'], {'db': True, 'redis': True})

    def test_unhealthy_when_db_down(self):
        with patch.object(HealthCheckView, '_check_db', return_value=False), \
             patch.object(HealthCheckView, '_check_redis', return_value=True):
            request = factory.get('/api/health/')
            response = self.view(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['status'], 'unhealthy')

    def test_unhealthy_when_redis_down(self):
        with patch.object(HealthCheckView, '_check_db', return_value=True), \
             patch.object(HealthCheckView, '_check_redis', return_value=False):
            request = factory.get('/api/health/')
            response = self.view(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['status'], 'unhealthy')

    def test_accessible_without_authentication(self):
        request = factory.get('/api/health/')
        response = self.view(request)
        self.assertIn(response.status_code, (200, 503))
