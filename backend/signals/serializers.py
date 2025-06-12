from __future__ import annotations

from rest_framework import serializers

from .models import Signal


class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = [
            'signal_id', 'signal_type', 'ticker_id',
            'confidence_score', 'generated_at', 'used_model', 'config_ig',
        ]


class SignalGenerationRequestSerializer(serializers.Serializer):
    ticker_id = serializers.IntegerField(required=True)
    config_id = serializers.IntegerField(required=True)
    # Elastyczne pole na dodatkowe parametry
    additional_params = serializers.JSONField(required=False)
