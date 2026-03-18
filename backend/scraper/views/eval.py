from rest_framework.views import APIView
from rest_framework.response import Response
from ..serializers import EvalRequestSerializer, EvalResponseSerializer
from ..services.data_service import DataService

class EvalView(APIView):
    """
    On-demand sentiment evaluation.
    """
    def post(self, request):
        serializer = EvalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = DataService()
        result = service.evaluate_sentiment(
            serializer.validated_data, 
            with_save=serializer.validated_data.get('with_save', False)
        )
        
        response_serializer = EvalResponseSerializer(result)
        return Response(response_serializer.data)

class PredictionsByDayView(APIView):
    """
    Aggregated prediction statistics optimized for performance.
    """
    def get(self, request):
        tickers = request.query_params.get('tickers', 'all')
        service = DataService()
        results = service.get_predictions_by_day(tickers)
        return Response(results)
