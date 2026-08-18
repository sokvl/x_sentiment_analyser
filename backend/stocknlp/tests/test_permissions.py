from types import SimpleNamespace

from django.test import SimpleTestCase
from django.test import override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from stocknlp.permissions import HasInterviewerKey
from stocknlp.permissions import IsOwner
from stocknlp.permissions import IsOwnerOrHasInterviewerKey

factory = APIRequestFactory()

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


class IsOwnerTests(SimpleTestCase):
    def test_authenticated_user_allowed(self):
        request = make_request('get', user=owner)
        self.assertTrue(IsOwner().has_permission(request, None))

    def test_anonymous_user_denied(self):
        request = make_request('get', user=anonymous)
        self.assertFalse(IsOwner().has_permission(request, None))


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
