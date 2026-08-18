from __future__ import annotations

import secrets

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission


class HasInterviewerKey(BasePermission):
    message = 'A valid access key is required.'

    def has_permission(self, request, view) -> bool:
        if request.method not in SAFE_METHODS:
            return False

        expected = settings.INTERVIEWER_ACCESS_KEY
        if not expected:
            return False

        provided = request.headers.get('X-Access-Key') or request.query_params.get('key')
        if not provided:
            return False

        return secrets.compare_digest(provided, expected)


class IsOwner(BasePermission):

    def has_permission(self, request, view) -> bool:
        if settings.RAW_DEBUG:
            return True
        return bool(request.user and request.user.is_authenticated)


class IsOwnerOrHasInterviewerKey(BasePermission):
    """Owner: full access. Valid interviewer key: read-only. Everyone else: nothing."""

    def has_permission(self, request, view) -> bool:
        return (
            IsOwner().has_permission(request, view)
            or HasInterviewerKey().has_permission(request, view)
        )


class ActionPermissionsMixin:
    """Per-action permission_classes overrides for a ViewSet.

    Declare `action_permission_classes = {'create': [IsOwner], ...}` on the
    ViewSet; any action not listed falls back to the view's own
    `permission_classes` (and from there to the global DRF default).
    """

    action_permission_classes: dict[str, list[type[BasePermission]]] = {}

    def get_permissions(self):
        classes = self.action_permission_classes.get(self.action)
        if classes is not None:
            return [cls() for cls in classes]
        return super().get_permissions()
