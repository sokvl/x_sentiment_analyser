from __future__ import annotations

from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConfigView
from .views import EvalView
from .views import PostViewSet
from .views import PredictionsByDayView
from .views import ScraperControlView
from .views import SourceViewSet

router = DefaultRouter()
router.register(r'sources', SourceViewSet)
router.register(r'posts', PostViewSet)

urlpatterns = [
    path(
        'scraper/<str:operation>/',
        ScraperControlView.as_view(), name='scraper-control',
    ),
    path(
        'predictions-by-day/', PredictionsByDayView.as_view(),
        name='predictions-by-day',
    ),
    path('eval/', EvalView.as_view(), name='eval'),
    path('', include(router.urls)),
    path('config/', ConfigView.as_view(), name='config-list'),
    path('config/<int:pk>/', ConfigView.as_view(), name='config-detail'),
]
