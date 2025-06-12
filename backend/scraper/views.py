from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Config
from .models import Post
from .models import Source
from .models import Ticker
from .serializers import ConfigSerializer
from .serializers import EvalRequestSerializer
from .serializers import EvalResponseSerializer
from .serializers import PostSerializer
from .serializers import SourceSerializer
# LIB
# DEBUG!!!
# INTERNALS


@method_decorator(csrf_exempt, name='dispatch')
class ScraperControlView(View):

    def post(self, request, operation):
        scraper_manager = apps.get_app_config('scraper').SCRAPER_MANAGER

        operation_handlers = {
            'start': self._handle_start,
            'config': self._handle_config,
            'pause': self._handle_pause,
            'resume': self._handle_resume,
            'stop': self._handle_stop,
            'restart': self._handle_restart,
        }

        handler = operation_handlers.get(
            operation, self._handle_invalid_operation,
        )
        return handler(request, scraper_manager)

    def get(self, request, operation):

        scraper_manager = apps.get_app_config('scraper').SCRAPER_MANAGER

        operation_handlers = {
            'logs': self._handle_logs,
        }

        handler = operation_handlers.get(operation, self._handle_no_data_found)
        return handler(request, scraper_manager)

    # =========================
    #    POST Operation Handlers
    # =========================

    def _handle_start(self, request, scraper_manager):
        """
        Start the scraper for 'twitter'.
        If 'twitter' scraper doesn't exist, create it before starting.
        """
        try:
            if not scraper_manager.get_scraper('twitter'):
                scraper_manager.set_scraper('twitter')
        except Exception as e:
            print(e)
            return JsonResponse({'message': 'There is no scraper to start. {e}'}, status=404)

        return JsonResponse({'message': 'Scraper started successfully.'}, status=200)

    def _handle_config(self, request, scraper_manager):
        """
        Update the configuration for a scraper. Requires the following fields:
        'crawl_interval', 'source', 'max_time_running', 'threads'.
        """
        required_fields = [
            'crawl_interval',
            'source', 'max_time_running', 'threads',
        ]
        config_data = request.POST.get('config')

        if not config_data:
            return JsonResponse(
                {
                    'error': 'Missing config data.',
                    'required_fields': required_fields,
                },
                status=400,
            )

        if not all(field in config_data for field in required_fields):
            return JsonResponse(
                {
                    'error': 'Invalid or missing configuration fields.',
                    'required_fields': required_fields,
                },
                status=400,
            )

        updated = scraper_manager.find_and_update_scraper_config(
            config_data['source'], config_data,
        )
        if updated:
            return JsonResponse(
                {
                    'message': 'Configuration updated successfully.',
                    'config': config_data,
                },
                status=200,
            )

        return JsonResponse(
            {
                'error': 'Selected source does not exist.',
                'source': config_data['source'],
            },
            status=404,
        )

    def _handle_pause(self, request, scraper_manager):
        source = request.POST.get('source')
        if not source:
            return JsonResponse({'error': 'Source is required to pause a scraper.'}, status=400)

        scraper = scraper_manager.get_scraper(source)
        if not scraper:
            return JsonResponse({'error': f"Scraper for source '{source}' not found."}, status=404)

        result = scraper_manager.access_scraper(source, 'pause')
        if not result:
            return JsonResponse({'error': 'Failed to pause the scraper.'}, status=500)

        if isinstance(result, dict) and 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)

        return JsonResponse({'message': f"Scraper for source '{source}' paused successfully."}, status=200)

    def _handle_resume(self, request, scraper_manager):
        source = request.POST.get('source')
        if not source:
            return JsonResponse({'error': 'Source is required to resume a scraper.'}, status=400)

        scraper = scraper_manager.get_scraper(source)
        if not scraper:
            return JsonResponse({'error': f"Scraper for source '{source}' not found."}, status=404)

        result = scraper_manager.access_scraper(source, 'resume')
        if not result:
            return JsonResponse({'error': 'Failed to resume the scraper.'}, status=500)

        if isinstance(result, dict) and 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)

        return JsonResponse({'message': f"Scraper for source '{source}' resumed successfully."}, status=200)

    def _handle_stop(self, request, scraper_manager):
        source = request.POST.get('source')
        if not source:
            return JsonResponse({'error': 'Source is required to stop a scraper.'}, status=400)

        scraper = scraper_manager.get_scraper(source)

        if not scraper:
            return JsonResponse({'error': f"Scraper for source '{source}' not found."}, status=404)

        try:
            scraper_manager.stop_scraper(source)
            return JsonResponse({'message': f"Scraper for source '{source}' stopped successfully."}, status=200)
        except Exception as e:
            return JsonResponse(
                {'error': f"An error occurred while stopping the scraper: {str(e)}"},
                status=500,
            )

    def _handle_restart(self, request, scraper_manager):
        source = request.POST.get('source')
        if not source:
            return JsonResponse({'error': 'Source is required to stop a scraper.'}, status=400)

        scraper = scraper_manager.get_scraper(source)

        if not scraper:
            return JsonResponse({'error': f"Scraper for source '{source}' not found."}, status=404)

        try:
            scraper_manager.restart_scraper(source)
            return JsonResponse({'message': f"Scraper for source '{source}' stopped successfully."}, status=200)
        except Exception as e:
            return JsonResponse(
                {'error': f"An error occurred while stopping the scraper: {str(e)}"},
                status=500,
            )

    def _handle_invalid_operation(self, request, scraper_manager):
        return JsonResponse({'error': 'Invalid operation'}, status=400)

    # =========================
    #    GET Operation Handlers
    # =========================

    def _handle_logs(self, request, scraper_manager):
        """
        Retrieve logs or state details of a given 'source' from the scraper manager.
        """
        source = request.GET.get('source')
        if not source:
            return JsonResponse({'error': 'Source is required to retrieve logs.'}, status=400)

        scraper_data = scraper_manager.access_scraper(source, 'get_state')
        if not scraper_data:
            return JsonResponse({'message': 'No data found'}, status=404)

        if isinstance(scraper_data, dict) and 'error' in scraper_data:
            # Return an error if the result indicates a problem
            return JsonResponse(
                {
                    'message': 'Disabled',
                    'error_details': scraper_data['error'],
                },
                status=200,
            )

        response_data = {
            'state': scraper_data.get('state', 'unknown'),
            'logs': list(scraper_data.get('logs', [])),
            'current_task': scraper_data.get('current_task_details', {}),
        }
        return JsonResponse(response_data, status=200)

    def _handle_no_data_found(self, request, scraper_manager):
        """
        Fallback for invalid or unrecognized GET operations.
        """
        return JsonResponse({'message': 'No data found'}, status=404)


class EvalView(APIView):
    def post(self, request):
        serializer = EvalRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tweet = serializer.validated_data['tweet']
        ticker = serializer.validated_data['ticker']
        with_save = serializer.validated_data['with_save']
        source_name = serializer.validated_data['source_name']
        tweet_date = serializer.validated_data['date']

        try:
            data_manager = apps.get_app_config('scraper').DATA_MANAGER
        except AttributeError as e:
            return Response(
                {'error': 'DataManager not initialized', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            result = data_manager.eval_sentiment(
                {
                    'text': tweet,
                    'ticker': ticker,
                    'source_name': source_name,
                    'date': tweet_date,
                }, with_save,
            )
        except ValueError as e:
            return Response(
                {
                    'error': 'Error during sentiment evaluation',
                    'details': str(e),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Unexpected error during sentiment evaluation',
                    'details': str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            response_serializer = EvalResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Error serializing response', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PredictionsByDayView(APIView):
    """
    View that returns the count of post predictions divided by days for given tickers or all.
    """

    def get(self, request):
        tickers_param = request.query_params.get(
            'tickers', 'all',
        )  # List of tickers or "all"
        max_date = now().date()  # Today's date
        min_date = max_date - timedelta(days=30)  # Up to one month back

        if tickers_param == 'all':
            tickers = Ticker.objects.all()
        else:
            ticker_symbols = tickers_param.split(',')
            tickers = Ticker.objects.filter(symbol__in=ticker_symbols)

        if not tickers.exists():
            return Response({'error': 'No valid tickers found.'}, status=status.HTTP_404_NOT_FOUND)

        results = []
        for ticker in tickers:
            aggregations = (
                Post.objects.filter(
                    related_ticker=ticker,
                    time_stamp__range=[min_date, max_date],
                )
                .annotate(day=TruncDate('time_stamp'))
                .values('day', 'post_prediction__prediction')
                .annotate(count=Count('id'))
            )

            predictions_by_day = {}
            for row in aggregations:
                date_str = row['day'].isoformat()
                pred = row['post_prediction__prediction']
                predictions_by_day.setdefault(date_str, {0: 0, 1: 0, 2: 0})[
                    pred
                ] = row['count']

            results.append({
                'ticker': ticker.symbol,
                'predictions': predictions_by_day,
            })

        return Response(results, status=status.HTTP_200_OK)


class ConfigView(APIView):
    def get(self, request, pk=None):
        if pk:
            config = get_object_or_404(Config, pk=pk)
            serializer = ConfigSerializer(config)
            return Response(serializer.data)

        active_param = request.query_params.get('active')
        if active_param is not None:
            active_param = active_param.lower()
            if active_param in ['true', '1']:
                configs = Config.objects.filter(active=True)
            elif active_param in ['false', '0']:
                configs = Config.objects.filter(active=False)
            else:
                return Response(
                    {'error': "Invalid value for 'active'. Use true/false or 1/0."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            configs = Config.objects.all()

        if not configs.exists():
            return Response(
                {'message': 'No configs found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ConfigSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        config = get_object_or_404(Config, pk=pk)
        serializer = ConfigSerializer(config, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        config = get_object_or_404(Config, pk=pk)
        data = request.data.get('config_string', {})
        for key, value in data.items():
            if key in config.config_string:
                config.config_string[key].update(value) if isinstance(
                    value, dict,
                ) else config.config_string[key].extend(value)
            else:
                config.config_string[key] = value
        config.save()
        serializer = ConfigSerializer(config)
        return Response(serializer.data)

    def delete(self, request, pk):
        config = get_object_or_404(Config, pk=pk)
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter, filters.OrderingFilter,
    ]
    search_fields = ['name']
    ordering_fields = ['name']


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related(
        'related_ticker', 'post_prediction',
    ).all()
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'related_ticker__symbol',
        'post_prediction__prediction',
    ]
    ordering_fields = ['time_stamp']
    ordering = ['-time_stamp']
