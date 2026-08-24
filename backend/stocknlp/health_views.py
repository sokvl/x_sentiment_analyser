from django.db import connection
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from stocknlp.tasks import get_redis


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {'db': self._check_db(), 'redis': self._check_redis()}
        healthy = all(checks.values())
        status_code = 200 if healthy else 503
        return Response(
            {'status': 'ok' if healthy else 'unhealthy', 'checks': checks},
            status=status_code,
        )

    def _check_db(self) -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return True
        except OperationalError:
            return False

    def _check_redis(self) -> bool:
        try:
            return bool(get_redis().ping())
        except Exception:
            return False
