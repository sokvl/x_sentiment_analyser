from rest_framework import serializers
from ..models import Config

class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = '__all__'

    def validate_config_string(self, value):
        if 'user_config' not in value or 'scrapers_config' not in value:
            raise serializers.ValidationError(
                "Config string must contain 'user_config' and 'scrapers_config' keys.",
            )
        if not isinstance(value['user_config'], dict):
            raise serializers.ValidationError(
                "'user_config' must be a dictionary.",
            )
        if not isinstance(value['scrapers_config'], list):
            raise serializers.ValidationError(
                "'scrapers_config' must be a list.",
            )
        return value
