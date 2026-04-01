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
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        date_str = request.query_params.get('date')

        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        elif date_str:
            end_date = parse_date(date_str)
            if not end_date:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
            start_date = end_date - timedelta(days=1)
        else:
            return Response({'error': 'Provide start_date & end_date, or date.'}, status=status.HTTP_400_BAD_REQUEST)

        tickers_param = request.query_params.get('tickers', 'all')
        used_model = request.query_params.get('used_model', 'LSTMCNNv1')
        try:
            config_id = int(request.query_params.get('config_id', 1))
        except (ValueError, TypeError):
            return Response({'error': 'config_id must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        with_save = request.query_params.get('with_save', 'false').lower() == 'true'

        service = SignalService()
        try:
            tickers = service.resolve_tickers(tickers_param)

            results = service.generate_for_tickers(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
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
