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
        
        for key, value in new_data.items():
            if key in config.config_string:
                if isinstance(value, dict) and isinstance(config.config_string[key], dict):
                    config.config_string[key].update(value)
                elif isinstance(value, list) and isinstance(config.config_string[key], list):
                    config.config_string[key].extend(value)
                else:
                    config.config_string[key] = value
            else:
                config.config_string[key] = value
        
        config.save()
        return Response(self.get_serializer(config).data)
