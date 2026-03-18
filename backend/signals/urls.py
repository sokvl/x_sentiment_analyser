from __future__ import annotations

from django.urls import path

from .views import PredictionReportView, ProcessCSVView, SignalListView
from signals.views.generation import SignalGenerationView

urlpatterns = [
    path('', SignalListView.as_view(), name='signal-list'),
    path('generate/', SignalGenerationView.as_view(), name='signal-generate'),
    path('process-csv/', ProcessCSVView.as_view(), name='signal-process-csv'),
    path('prediction-report/', PredictionReportView.as_view(), name='signal-prediction-report'),
]
