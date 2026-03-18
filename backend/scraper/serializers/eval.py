from rest_framework import serializers

class EvalRequestSerializer(serializers.Serializer):
    tweet = serializers.CharField(required=True)
    ticker = serializers.CharField(required=True)
    source_name = serializers.CharField()
    date = serializers.DateField()
    with_save = serializers.BooleanField(default=False)

class EvalResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    ticker = serializers.CharField()
    processed_text = serializers.ListField(
        child=serializers.IntegerField(), help_text='Token indices from preprocessor',
    )
    predicted_sentiment = serializers.IntegerField(source='prediction')
    predicted_probabilities = serializers.ListField(
        child=serializers.FloatField(),
    )
