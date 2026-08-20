from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PredictionReportView, ProcessCSVView, ProcessCSVJobStatusView, SignalListView, UploadedFileViewSet,
)
from signals.views.generation import SignalGenerationView

router = DefaultRouter()
router.register('files', UploadedFileViewSet, basename='files')

urlpatterns = [
    path('', SignalListView.as_view(), name='signal-list'),
    path('generate/', SignalGenerationView.as_view(), name='signal-generate'),
    path('process-csv/', ProcessCSVView.as_view(), name='signal-process-csv'),
    path('process-csv/<str:job_id>/', ProcessCSVJobStatusView.as_view(), name='signal-process-csv-status'),
    path('prediction-report/', PredictionReportView.as_view(), name='signal-prediction-report'),
    path('', include(router.urls)),
]
