from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd
import yfinance as yf
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticker
from .serializers import TickerSerializer


class TickerViewSet(viewsets.ModelViewSet):
    """CRUD for tickers with pagination, search & ordering."""
    serializer_class = TickerSerializer
    queryset = Ticker.objects.all()

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter, filters.OrderingFilter,
    ]
    filterset_fields = ['type']
    search_fields = ['symbol', 'full_name']
    ordering_fields = ['symbol', 'created_at']
    ordering = ['symbol']

    def retrieve(self, request, pk=None):
        ticker = get_object_or_404(Ticker, pk=pk)
        serializer = TickerSerializer(ticker)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = TickerSerializer(data=request.data, many=is_many)
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, pk=None):
        ticker = get_object_or_404(Ticker, pk=pk)
        serializer = TickerSerializer(ticker, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        ticker = get_object_or_404(Ticker, pk=pk)
        ticker.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list_by_type(self, request, type=None):
        queryset = Ticker.objects.filter(type=type)
        serializer = TickerSerializer(queryset, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        ticker = get_object_or_404(Ticker, pk=pk)
        serializer = TickerSerializer(ticker, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockDataView(APIView):

    def get(self, request):
        tickers = request.query_params.get(
            'tickers', 'all',
        )  # Ticker lub "all"
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not end_date:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date:
            start_date = end_date
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        start_date = start_date - timedelta(days=1)

        if tickers == 'all':
            ticker_objects = Ticker.objects.all()
            ticker_list = [ticker.symbol[1:] for ticker in ticker_objects]
        else:
            ticker_list = tickers.split(',')
            ticker_objects = Ticker.objects.filter(symbol__in=ticker_list)

        if not ticker_objects.exists():
            return Response({'error': 'No valid tickers found in the database.'}, status=status.HTTP_404_NOT_FOUND)
        result = {}
        for ticker in ticker_list:
            try:
                data = yf.download(
                    tickers=ticker,
                    period='1d',
                    progress=False,
                )
                if data.empty:
                    result[ticker] = {
                        'error': 'No price data found for this ticker in the specified date range.',
                    }
                else:
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = [
                            ' '.join(col).strip()
                            for col in data.columns.values
                        ]
                    result[ticker] = data.reset_index().to_dict(
                        orient='records',
                    )
            except Exception as e:
                result[ticker] = {'error': f"Failed to fetch data: {str(e)}"}

        return Response(result, status=status.HTTP_200_OK)
