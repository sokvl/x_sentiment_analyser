from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.ticker_service import TickerService

class StockDataView(APIView):
    """
    Fetches OHLCV market data from yfinance for a set of tickers.
    DRF automatically handles NotFound (404) and ValidationError (400).
    """
    def get(self, request):
        tickers_param = request.query_params.get('tickers', 'all')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        service = TickerService()
        symbols, _ = service.resolve_tickers(tickers_param)
        start, end = service.parse_date_range(start_date, end_date)
        result = service.fetch_stock_data(symbols, start, end)
        return Response(result, status=status.HTTP_200_OK)
