import logging
from typing import List, Any
from django.apps import apps
from django.db.models import QuerySet
from ..models import Signal
from ..constants import (
    BUY_THRESHOLD, SELL_THRESHOLD, SENTIMENT_WEIGHTS,
)

logger = logging.getLogger(__name__)

class SignalService:
    """
    Service for generating and managing trading signals based on sentiment analysis.
    """

    def resolve_tickers(self, tickers_param: str) -> List[Any]:
        """
        Resolves a comma-separated string of symbols or 'all' to a list of Ticker objects.
        """
        Ticker = apps.get_model('tickers', 'Ticker')
        if tickers_param.lower() == 'all':
            return list(Ticker.objects.all())

        symbols = [s.strip().strip('$').upper() for s in tickers_param.split(',')]

        tickers = list(Ticker.objects.filter(symbol__in=symbols))
        if not tickers:
            raise ValueError(f"No tickers found for symbols: {tickers_param}")
        return tickers

    def get_posts_in_range(self, ticker: Any, start_date: Any, end_date: Any) -> QuerySet:
        """
        Retrieves posts for a specific ticker within a date range.
        Historically, the user's logic often looks at [single_date - 1, single_date].
        """
        Post = apps.get_model('scraper', 'Post')
        return Post.objects.filter(
            related_ticker=ticker,
            time_stamp__date__range=[start_date, end_date]
        ).select_related('post_prediction')

    def calculate_sentiment_score(self, posts) -> float:
        """
        Calculates a weighted sentiment score using the full probability
        distribution from each post's prediction.

        Score per post = sum(weight * probability) for all classes.
        Final score = average across posts.
        """
        if not posts:
            return 0.0

        total_score = 0.0
        count = 0

        for post in posts:
            probs = post.post_prediction.probabilities

            if not probs or len(probs) < len(SENTIMENT_WEIGHTS):
                continue

            total_score += sum(w * float(p) for w, p in zip(SENTIMENT_WEIGHTS, probs))
            count += 1

        if count == 0:
            return 0.0

        return round(total_score / count, 2)

    def compute_batch_score(self, probabilities: List[List[float]], weights: List[float]) -> float:
        """
        Calculates a weighted score for a batch of predictions (e.g. from CSV).
        Score per row = sum(w * p for w, p in zip(weights, prob)).
        Final score = average across rows.
        """
        total_score = 0.0
        count = 0

        for prob in probabilities:
            if not prob or len(prob) != len(weights):
                continue

            total_score += sum(w * float(p) for w, p in zip(weights, prob))
            count += 1

        if count == 0:
            return 0.0
        return round(total_score / count, 2)

    def determine_signal_type(self, score: float) -> str:
        """
        Maps a sentiment score to a signal type (BUY, SELL, HOLD).
        """
        if score >= BUY_THRESHOLD:
            return 'BUY'
        elif score <= SELL_THRESHOLD:
            return 'SELL'
        else:
            return 'HOLD'

    def generate_for_tickers(self, tickers: List[Any], start_date: Any, end_date: Any, used_model: str, with_save: bool, config_id: int) -> dict:
        """
        Generates and optionally saves signals for multiple tickers for a specific date range.
        """
        results = {}
        Config = apps.get_app_config('scraper').get_model('Config')
        try:
            config = Config.objects.get(config_id=config_id)
        except Config.DoesNotExist:
            raise ValueError(f"Config with ID {config_id} not found")

        for ticker in tickers:
            posts = self.get_posts_in_range(ticker, start_date, end_date)
            score = self.calculate_sentiment_score(posts)
            signal_type = self.determine_signal_type(score)

            signal_data = {
                'ticker': ticker.symbol,
                'signal_type': signal_type,
                'confidence_score': score,
                'tweet_count': posts.count(),
                'date': end_date.isoformat()
            }

            if with_save:
                Signal.objects.create(
                    signal_type=signal_type,
                    ticker=ticker,
                    confidence_score=score,
                    used_model=used_model,
                    config=config,
                )

            results[ticker.symbol] = signal_data

        return results
