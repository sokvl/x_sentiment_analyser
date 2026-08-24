from django.apps import apps
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class AvailableModelsView(APIView):
    """
    Lists sentiment models known to the registry, split by availability.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        registry = apps.get_app_config('scraper').MODEL_REGISTRY
        return Response({
            'available': registry.available_models,
            'unavailable': registry.unavailable_models,
        })
