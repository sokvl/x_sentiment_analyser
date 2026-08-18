from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PredictionReportView, ProcessCSVView, SignalListView, UploadedFileViewSet
from signals.views.generation import SignalGenerationView

router = DefaultRouter()
router.register('files', UploadedFileViewSet, basename='files')

urlpatterns = [
    path('', SignalListView.as_view(), name='signal-list'),
    path('generate/', SignalGenerationView.as_view(), name='signal-generate'),
    path('process-csv/', ProcessCSVView.as_view(), name='signal-process-csv'),
    path('prediction-report/', PredictionReportView.as_view(), name='signal-prediction-report'),
    path('', include(router.urls)),
]
