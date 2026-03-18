from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from ..services.signal_service import SignalService
from ..utils import parse_date

class SignalGenerationView(APIView):
    """
    Generate BUY/SELL/HOLD signals from existing post predictions.
    Matches the logic provided in the user's snippet (2-day window).
    """
    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'date parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        parsed_date = parse_date(date_str)
        if not parsed_date:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        tickers_param = request.query_params.get('tickers', 'all')
        used_model = request.query_params.get('used_model', 'LSTMCNNv1')
        config_id = int(request.query_params.get('config_id', 1))
        with_save = request.query_params.get('with_save', 'false').lower() == 'true'

        service = SignalService()
        try:
            tickers = service.resolve_tickers(tickers_param)
            
            # The snippet uses [date - 1, date]
            start_date = parsed_date - timedelta(days=1)
            results = service.generate_for_tickers(
                tickers=tickers,
                start_date=start_date,
                end_date=parsed_date,
                used_model=used_model,
                with_save=with_save,
                config_id=config_id,
            )
            return Response(results, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
             return Response(
                {'error': 'Signal generation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
