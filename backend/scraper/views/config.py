from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Config
from ..serializers import ConfigSerializer

class ConfigViewSet(viewsets.ModelViewSet):
    """
    Standard ViewSet for managing scraper configurations.
    """
    queryset = Config.objects.all()
    serializer_class = ConfigSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self.request.query_params.get('active')
        if active is not None:
            queryset = queryset.filter(active=active.lower() in ['true', '1'])
        return queryset

    @action(detail=True, methods=['patch'])
    def update_config_string(self, request, pk=None):
        config = self.get_object()
        new_data = request.data.get('config_string', {})

        merged = dict(config.config_string)
        for key, value in new_data.items():
            current = merged.get(key)
            if isinstance(value, dict) and isinstance(current, dict):
                merged[key] = {**current, **value}
            elif isinstance(value, list) and isinstance(current, list):
                merged[key] = current + [item for item in value if item not in current]
            else:
                merged[key] = value

        serializer = self.get_serializer(
            config, data={'config_string': merged}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
