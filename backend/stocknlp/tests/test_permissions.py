from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase
from django.test import TestCase
from django.test import override_settings
from django.urls import path
from rest_framework.authentication import SessionAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from stocknlp.permissions import HasInterviewerKey
from stocknlp.permissions import IsOwner
from stocknlp.permissions import IsOwnerOrHasInterviewerKey

not_debug = override_settings(RAW_DEBUG=False)

factory = APIRequestFactory()


class _OwnerOnlyProbeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOwner]

    def get(self, request):
        return Response({'ok': True})


urlpatterns = [path('__owner_probe__/', _OwnerOnlyProbeView.as_view())]

owner = SimpleNamespace(is_authenticated=True)
anonymous = SimpleNamespace(is_authenticated=False)


def make_request(method='get', user=anonymous, key=None, in_header=True, **extra):
    if key is not None:
        if in_header:
            extra['HTTP_X_ACCESS_KEY'] = key
            django_request = getattr(factory, method)('/api/posts/', **extra)
        else:
            django_request = getattr(factory, method)('/api/posts/', {'key': key}, **extra)
    else:
        django_request = getattr(factory, method)('/api/posts/', **extra)

    request = Request(django_request)
    request._user = user
    return request


@override_settings(INTERVIEWER_ACCESS_KEY='super-secret')
class HasInterviewerKeyTests(SimpleTestCase):
    def test_correct_key_in_header_allows_get(self):
        request = make_request('get', key='super-secret', in_header=True)
        self.assertTrue(HasInterviewerKey().has_permission(request, None))

    def test_correct_key_in_query_param_allows_get(self):
        request = make_request('get', key='super-secret', in_header=False)
        self.assertTrue(HasInterviewerKey().has_permission(request, None))

    def test_wrong_key_denied(self):
        request = make_request('get', key='wrong-key', in_header=True)
        self.assertFalse(HasInterviewerKey().has_permission(request, None))

    def test_missing_key_denied(self):
        request = make_request('get')
        self.assertFalse(HasInterviewerKey().has_permission(request, None))

    def test_correct_key_on_write_method_denied(self):
        request = make_request('post', key='super-secret', in_header=True)
        self.assertFalse(HasInterviewerKey().has_permission(request, None))

    @override_settings(INTERVIEWER_ACCESS_KEY='')
    def test_disabled_when_setting_is_empty(self):
        # Even a request that "matches" an empty expected key must be denied —
        # unset config means the interviewer path is off, not wide open.
        request = make_request('get', key='', in_header=True)
        self.assertFalse(HasInterviewerKey().has_permission(request, None))


@not_debug
class IsOwnerTests(SimpleTestCase):
    def test_authenticated_user_allowed(self):
        request = make_request('get', user=owner)
        self.assertTrue(IsOwner().has_permission(request, None))

    def test_anonymous_user_denied(self):
        request = make_request('get', user=anonymous)
        self.assertFalse(IsOwner().has_permission(request, None))


@not_debug
@override_settings(INTERVIEWER_ACCESS_KEY='super-secret')
class IsOwnerOrHasInterviewerKeyTests(SimpleTestCase):
    def test_owner_allowed_on_write_without_key(self):
        request = make_request('post', user=owner)
        self.assertTrue(IsOwnerOrHasInterviewerKey().has_permission(request, None))

    def test_non_owner_with_valid_key_allowed_on_read(self):
        request = make_request('get', user=anonymous, key='super-secret')
        self.assertTrue(IsOwnerOrHasInterviewerKey().has_permission(request, None))

    def test_non_owner_with_valid_key_denied_on_write(self):
        request = make_request('post', user=anonymous, key='super-secret')
        self.assertFalse(IsOwnerOrHasInterviewerKey().has_permission(request, None))

    def test_non_owner_without_key_denied(self):
        request = make_request('get', user=anonymous)
        self.assertFalse(IsOwnerOrHasInterviewerKey().has_permission(request, None))


@not_debug
@override_settings(ROOT_URLCONF=__name__)
class IsOwnerSessionAuthenticationIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='pw123456')
        self.client = APIClient()

    def test_logged_in_session_is_allowed(self):
        self.client.login(username='owner', password='pw123456')
        response = self.client.get('/__owner_probe__/')
        self.assertEqual(response.status_code, 200)

    def test_no_session_is_denied(self):
        response = self.client.get('/__owner_probe__/')
        self.assertEqual(response.status_code, 403)

    def test_logged_out_session_is_denied(self):
        self.client.login(username='owner', password='pw123456')
        self.client.logout()
        response = self.client.get('/__owner_probe__/')
        self.assertEqual(response.status_code, 403)
