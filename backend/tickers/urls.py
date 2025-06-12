from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import StockDataView
from .views import TickerViewSet

router = DefaultRouter()
router.register(r'tickers', TickerViewSet, basename='ticker')

urlpatterns = [
    path('stock-data/', StockDataView.as_view(), name='stock-data'),
] + router.urls
