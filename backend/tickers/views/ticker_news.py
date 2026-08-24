from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from stocknlp.permissions import IsOwnerOrHasInterviewerKey
from ..services.ticker_service import TickerService

class TickerNewsView(APIView):
    """
    Fetches recent news headlines from yfinance for a set of tickers.
    DRF automatically handles NotFound (404) and ValidationError (400).
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def get(self, request):
        tickers_param = request.query_params.get('tickers', 'all')
        count_param = request.query_params.get('count')

        service = TickerService()
        symbols, _ = service.resolve_tickers(tickers_param)
        count = service.parse_news_count(count_param)
        result = service.fetch_news(symbols, count)
        return Response(result, status=status.HTTP_200_OK)
