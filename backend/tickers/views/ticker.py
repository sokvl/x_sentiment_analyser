from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Ticker
from ..serializers import TickerSerializer

class TickerViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD ViewSet for Tickers.
    """
    serializer_class = TickerSerializer
    queryset = Ticker.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type']
    search_fields = ['symbol', 'full_name']
    ordering_fields = ['symbol', 'created_at']
    ordering = ['symbol']

    def create(self, request, *args, **kwargs):
        """Support bulk creation by accepting a list of objects."""
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='by-type/(?P<type>[^/.]+)')
    def list_by_type(self, request, type=None):
        """
        Filter tickers by type.
        """
        queryset = self.get_queryset().filter(type=type)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
