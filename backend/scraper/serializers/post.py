from rest_framework import serializers
from tickers.serializers import TickerSerializer
from ..models import Post, PostMeta, PostPrediction, Content

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
