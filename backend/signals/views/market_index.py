from datetime import datetime
from django.apps import apps
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from stocknlp.permissions import IsOwnerOrHasInterviewerKey
from ..services.signal_service import SignalService
from ..utils import parse_date, date_range, log_and_get_safe_message

class MarketOptimismIndexView(APIView):
    """
    Aggregates sentiment across all scraped posts (all tickers) into a
    daily market optimism index in range [-1, 1].
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        Post = apps.get_model('scraper', 'Post')

        if start_date_str:
            start_date = parse_date(start_date_str)
            if not start_date:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            earliest = Post.objects.order_by('time_stamp').values_list('time_stamp', flat=True).first()
            start_date = earliest.date() if earliest else datetime.now().date()

        if end_date_str:
            end_date = parse_date(end_date_str)
            if not end_date:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            latest = Post.objects.order_by('-time_stamp').values_list('time_stamp', flat=True).first()
            end_date = latest.date() if latest else datetime.now().date()

        if start_date > end_date:
            return Response(
                {'error': 'start_date cannot be after end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = SignalService()
        try:
            series = self._build_series(service, start_date, end_date)
            return Response({
                'series': series,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = log_and_get_safe_message(e, 'Market index generation failed')
            return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_series(self, service: SignalService, start_date, end_date) -> list:
        all_posts = service.get_all_posts_in_range(start_date, end_date)
        posts_by_date = {}
        for post in all_posts:
            d = post.time_stamp.date().isoformat()
            posts_by_date.setdefault(d, []).append(post)

        series = []
        for day in date_range(start_date, end_date):
            date_str = day.isoformat()
            day_posts = posts_by_date.get(date_str, [])
            if not day_posts:
                continue
            series.append({
                'date': date_str,
                'index': service.calculate_sentiment_score(day_posts),
                'tweet_count': len(day_posts),
            })
        return series
