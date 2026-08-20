from django.conf import settings
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stocknlp.permissions import ActionPermissionsMixin, IsOwner
from ..models import Ticker
from ..serializers import TickerSerializer


class TickerViewSet(ActionPermissionsMixin, viewsets.ModelViewSet):
    """
    Standard CRUD ViewSet for Tickers.
    """
    permission_classes = [AllowAny]
    action_permission_classes = {
        'create': [IsOwner],
        'update': [IsOwner],
        'partial_update': [IsOwner],
        'destroy': [IsOwner],
        'list_by_type': [AllowAny],
    }
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
        if is_many and len(request.data) > settings.MAX_TICKER_BULK_CREATE:
            return Response(
                {
                    'error': f"Cannot create more than {settings.MAX_TICKER_BULK_CREATE} "
                             f"tickers in a single request ({len(request.data)} given).",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
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
