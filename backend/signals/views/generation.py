from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from stocknlp.permissions import IsOwner
from ..services.signal_service import SignalService
from ..utils import parse_date, log_and_get_safe_message

class SignalGenerationView(APIView):
    """
    Generate BUY/SELL/HOLD signals from existing post predictions.
    Matches the logic provided in the user's snippet (2-day window).
    """
    permission_classes = [IsOwner]
    throttle_scope = 'signal_generation'

    def get(self, request):
        """Read-only preview: never persists Signal rows, regardless of params."""
        return self._generate(request, with_save=False)

    def post(self, request):
        """Generates signals and, when requested, persists them as Signal rows."""
        with_save = request.data.get('with_save', request.query_params.get('with_save', 'false'))
        with_save = str(with_save).lower() == 'true'
        return self._generate(request, with_save=with_save)

    def _generate(self, request, with_save: bool):
        params = request.data if request.method == 'POST' else request.query_params

        start_date_str = params.get('start_date')
        end_date_str = params.get('end_date')
        date_str = params.get('date')

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

        tickers_param = params.get('tickers', 'all')
        used_model = params.get('used_model', 'LSTMCNNv1')
        try:
            config_id = int(params.get('config_id', 1))
        except (ValueError, TypeError):
            return Response({'error': 'config_id must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

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
            message = log_and_get_safe_message(e, 'Signal generation failed')
            return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
