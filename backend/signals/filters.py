from __future__ import annotations

import django_filters

from .models import Signal


class SignalFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name='generated_at', lookup_expr='gte',
    )
    end_date = django_filters.DateFilter(
        field_name='generated_at', lookup_expr='lte',
    )
    ticker_id = django_filters.NumberFilter(
        field_name='ticker_id__ticker_id',
    )  # Filtr po ticker_id

    class Meta:
        model = Signal
        fields = ['ticker_id', 'start_date', 'end_date']
