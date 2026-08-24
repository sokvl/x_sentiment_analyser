from __future__ import annotations

import secrets

from django.contrib import admin, messages

from .models import InterviewerKey


@admin.register(InterviewerKey)
class InterviewerKeyAdmin(admin.ModelAdmin):
    list_display = ('label', 'prefix', 'usage_count', 'last_used_at', 'expires_at', 'revoked_at', 'created_at')
    readonly_fields = ('prefix', 'hashed_secret', 'usage_count', 'last_used_at', 'created_at')

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('label', 'expires_at')
        return ('label', 'prefix', 'hashed_secret', 'usage_count', 'last_used_at', 'created_at', 'expires_at', 'revoked_at')

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        prefix = secrets.token_hex(4)
        secret = secrets.token_urlsafe(32)
        obj.prefix = prefix
        obj.hashed_secret = InterviewerKey.hash_secret(secret)
        super().save_model(request, obj, form, change)

        self.message_user(
            request,
            f'New interviewer key (copy now, shown only once): {prefix}.{secret}',
            level=messages.WARNING,
        )
