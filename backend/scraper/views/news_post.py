from django.apps import apps
from rest_framework.views import APIView
from rest_framework.response import Response
from stocknlp.permissions import IsOwnerOrHasInterviewerKey

class NewsPostListView(APIView):
    """
    Lists FinBERT-scored Finnhub news articles.
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def get(self, request):
        NewsPost = apps.get_model('scraper', 'NewsPost')
        tickers_param = request.query_params.get('tickers', 'all')

        qs = NewsPost.objects.select_related('ticker', 'news_prediction')
        if tickers_param != 'all':
            symbols = [s.strip().upper() for s in tickers_param.split(',')]
            qs = qs.filter(ticker__symbol__in=symbols)

        results = [{
            'ticker': n.ticker.symbol if n.ticker else None,
            'headline': n.headline,
            'summary': n.summary,
            'url': n.url,
            'publisher': n.publisher,
            'category': n.category,
            'published_at': n.published_at.isoformat(),
            'prediction': n.news_prediction.prediction,
            'probabilities': n.news_prediction.probabilities,
        } for n in qs[:100]]

        return Response(results)
