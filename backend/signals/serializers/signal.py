from rest_framework import serializers
from ..models import Signal

class SignalSerializer(serializers.ModelSerializer):
    """Serializer for the Signal model."""
    class Meta:
        model = Signal
        fields = [
            'signal_id', 'signal_type', 'ticker',
            'confidence_score', 'generated_at', 'used_model', 'config',
        ]
        read_only_fields = ['signal_id', 'generated_at']
