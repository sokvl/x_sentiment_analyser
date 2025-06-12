from __future__ import annotations

from rest_framework import serializers

from .models import Config
from .models import Content
from .models import Post
from .models import PostMeta
from .models import PostPrediction
from .models import Source
from .models import Ticker


class EvalRequestSerializer(serializers.Serializer):
    tweet = serializers.CharField(required=True)
    ticker = serializers.CharField(required=True)
    source_name = serializers.CharField()
    date = serializers.DateField()
    with_save = serializers.BooleanField(default=False)


class EvalResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    ticker = serializers.CharField()
    processed_text = serializers.CharField()
    predicted_sentiment = serializers.IntegerField(source='prediction')
    predicted_probabilities = serializers.ListField(
        child=serializers.FloatField(),
    )


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


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'updated_at',
            'is_active',
            'is_deleted',
        ]


class PostMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMeta
        fields = '__all__'


class PostPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostPrediction
        fields = [
            'prediction_id', 'prediction',
            'probabilities', 'model_name', 'created_at',
        ]


class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = '__all__'


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'


class PostSerializer(serializers.ModelSerializer):
    post_metadata = PostMetaSerializer(read_only=True)
    post_prediction = PostPredictionSerializer(read_only=True)
    related_ticker = TickerSerializer(read_only=True)
    related_content = ContentSerializer(read_only=True)

    class Meta:
        model = Post
        fields = '__all__'
