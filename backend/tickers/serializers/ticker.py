from rest_framework import serializers
from ..models import Ticker

class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = ['ticker_id', 'type', 'symbol', 'full_name', 'created_at', 'updated_at']
        read_only_fields = ['ticker_id', 'created_at', 'updated_at']
