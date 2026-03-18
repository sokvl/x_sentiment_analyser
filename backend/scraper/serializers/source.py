from rest_framework import serializers
from ..models import Source

class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            'source_id',
            'name',
            'base_url',
            'login_required',
            'credentials_id',
            'category',
        ]
