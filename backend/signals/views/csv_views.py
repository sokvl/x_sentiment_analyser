from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.csv_service import CSVProcessingService
from ..utils import get_data_manager

class ProcessCSVView(APIView):
    """
    Upload a CSV of tweets for batch LLM evaluation.
    Matches the logic and flow of the user's provided snippet.
    """
    def post(self, request):
        file = request.FILES.get('file')
        model_id = request.data.get('model_id')
        if not file or not file.name.endswith('.csv'):
            return Response(
                {'error': 'Invalid file format. Please upload a CSV file.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data_manager, error = get_data_manager()
        if not data_manager:
            return Response(
                {'error': 'DataManager not initialized', 'details': error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            service = CSVProcessingService()
            results, errors = service.process(file, model_id=model_id)
            return Response({'results': results, 'errors': errors}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': 'Error processing CSV file', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
