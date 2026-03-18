from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Source
from ..serializers import SourceSerializer
from ..services.scraper_service import ScraperService

class SourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sources with integrated Scraper control actions.
    """
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    @action(detail=True, methods=['post'], url_path='control/(?P<scraper_action>[^/.]+)')
    def control(self, request, pk=None, scraper_action=None):
        source = self.get_object()
        service = ScraperService()
        
        valid_actions = ['start', 'pause', 'resume', 'stop', 'restart']
        if scraper_action not in valid_actions:
            return Response(
                {"error": f"Invalid action. Expected one of {valid_actions}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            method = getattr(service, scraper_action)
            result = method(source.name)
            return Response(result)
        except (ValueError, RuntimeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        source = self.get_object()
        service = ScraperService()
        try:
            return Response(service.logs(source.name))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
