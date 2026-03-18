from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.scraper_service import ScraperService
from ..serializers import ConfigSerializer

class ScraperControlView(APIView):
    """
    Compatibility view for legacy /scraper/{action}/ endpoints.
    """
    def post(self, request, action):
        valid_actions = ['start', 'pause', 'resume', 'stop', 'restart']
        if action not in valid_actions:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        
        source_name = request.data.get('source')
        if not source_name:
            return Response({"error": "source is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        service = ScraperService()
        try:
            method = getattr(service, action)
            return Response(method(source_name))
        except (ValueError, RuntimeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ScraperLogsView(APIView):
    """
    Compatibility view for legacy /scraper/logs/ endpoint.
    """
    def get(self, request):
        source_name = request.query_params.get("source")
        if not source_name:
            return Response({"error": "source parameter required"}, status=status.HTTP_400_BAD_REQUEST)
        service = ScraperService()
        try:
            return Response(service.logs(source_name))
        except ValueError:
            return Response({
                "state": "unknown",
                "logs": [],
                "current_task": {},
                "message": "Scraper is not running"
            }, status=status.HTTP_200_OK)

class ScraperConfigView(APIView):
    """
    Compatibility view for legacy /scraper/config/ endpoint.
    """
    def post(self, request):
        serializer = ConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = ScraperService()
        try:
            return Response(service.update_config(serializer.validated_data))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
