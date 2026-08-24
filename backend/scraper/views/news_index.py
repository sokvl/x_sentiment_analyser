from datetime import datetime
from django.apps import apps
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from stocknlp.permissions import IsOwnerOrHasInterviewerKey
from signals.constants import SENTIMENT_WEIGHTS
from signals.utils import parse_date, date_range, log_and_get_safe_message

class NewsOptimismIndexView(APIView):
    """
    Aggregates sentiment across all FinBERT-scored Finnhub news articles into
    a daily news optimism index in range [-1, 1].
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        NewsPost = apps.get_model('scraper', 'NewsPost')

        if start_date_str:
            start_date = parse_date(start_date_str)
            if not start_date:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            earliest = NewsPost.objects.order_by('published_at').values_list('published_at', flat=True).first()
            start_date = earliest.date() if earliest else datetime.now().date()

        if end_date_str:
            end_date = parse_date(end_date_str)
            if not end_date:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            latest = NewsPost.objects.order_by('-published_at').values_list('published_at', flat=True).first()
            end_date = latest.date() if latest else datetime.now().date()

        if start_date > end_date:
            return Response(
                {'error': 'start_date cannot be after end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            series = self._build_series(NewsPost, start_date, end_date)
            return Response({
                'series': series,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = log_and_get_safe_message(e, 'News index generation failed')
            return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _calculate_sentiment_score(self, articles) -> float:
        if not articles:
            return 0.0

        total_score = 0.0
        count = 0

        for article in articles:
            probs = article.news_prediction.probabilities

            if not probs or len(probs) < len(SENTIMENT_WEIGHTS):
                continue

            total_score += sum(w * float(p) for w, p in zip(SENTIMENT_WEIGHTS, probs))
            count += 1

        if count == 0:
            return 0.0

        return round(total_score / count, 2)

    def _build_series(self, NewsPost, start_date, end_date) -> list:
        all_articles = NewsPost.objects.filter(
            published_at__date__range=[start_date, end_date],
        ).select_related('news_prediction')

        articles_by_date = {}
        for article in all_articles:
            d = article.published_at.date().isoformat()
            articles_by_date.setdefault(d, []).append(article)

        series = []
        for day in date_range(start_date, end_date):
            date_str = day.isoformat()
            day_articles = articles_by_date.get(date_str, [])
            if not day_articles:
                continue
            series.append({
                'date': date_str,
                'index': self._calculate_sentiment_score(day_articles),
                'article_count': len(day_articles),
            })
        return series
