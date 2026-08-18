from rest_framework import generics
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Signal
from ..serializers import SignalSerializer
from ..filters import SignalFilter

class SignalListView(generics.ListAPIView):
    """List all signals with filtering by date and ticker."""
    permission_classes = [AllowAny]
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SignalFilter
