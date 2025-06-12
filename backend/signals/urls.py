from __future__ import annotations

from django.urls import path

from .views import PredictionReportView
from .views import ProcessCSVView
from .views import SignalGenerationView
from .views import SignalListView

urlpatterns = [
    path(
        'api/signals/',
        SignalListView.as_view(),
        name='signal-list',
    ),
    path('generate/', SignalGenerationView.as_view(), name='signal-generate'),
    path('process-csv/', ProcessCSVView.as_view(), name='process-csv'),
    path('prediction-report/', PredictionReportView.as_view(), name='process-csv'),
]
