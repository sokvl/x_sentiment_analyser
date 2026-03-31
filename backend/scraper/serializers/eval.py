from rest_framework import serializers

class EvalRequestSerializer(serializers.Serializer):
    tweet = serializers.CharField(required=True)
    ticker = serializers.CharField(required=True)
    source_name = serializers.CharField()
    date = serializers.DateField()
    with_save = serializers.BooleanField(default=False)
    model_id = serializers.CharField(required=False, default=None)

class EvalResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    cleaned_text = serializers.CharField()
    ticker = serializers.CharField()
    predicted_sentiment = serializers.IntegerField(source='prediction')
    predicted_probabilities = serializers.ListField(
        child=serializers.FloatField(),
    )
