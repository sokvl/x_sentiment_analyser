import logging
from typing import List, Union, Any
from django.apps import apps
from django.db.models import QuerySet
from ..models import Signal
from ..constants import (
    BUY_THRESHOLD, SELL_THRESHOLD,
    PREDICTION_NEGATIVE_WEIGHT, PREDICTION_POSITIVE_WEIGHT
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
        
        symbols = [s.strip().upper() for s in tickers_param.split(',')]
        # Handle $ prefix if necessary
        normalized_symbols = [s if s.startswith('$') else f"${s}" for s in symbols]
        
        tickers = list(Ticker.objects.filter(symbol__in=normalized_symbols))
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

    def calculate_sentiment_score(self, posts: Union[List[Any], QuerySet], weights: Union[List[float], None] = None) -> float:
        """
        Calculates a weighted sentiment score using probabilities from post_prediction.
        Following the user's provided logic:
        Sum(weight * probability) / total_weight
        """
        if not posts:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for post in posts:
            pred = post.post_prediction.prediction
            probs = post.post_prediction.probabilities
            
            if not probs or len(probs) < 3:
                continue
                
            w0 = probs[0] # Neg
            w2 = probs[2] # Pos
            
            if pred == 0:
                weighted_sum += -1.0 * float(w0)
                total_weight += float(w0)
            elif pred == 2:
                weighted_sum += 1.0 * float(w2)
                total_weight += float(w2)
                
        if total_weight == 0:
            return 0.0
            
        score = weighted_sum / total_weight
        return round(score, 2)

    def compute_batch_score(self, sentiments: List[int], probabilities: List[List[float]], weights: List[float]) -> float:
        """
        Calculates a weighted score for a batch of predictions (e.g. from CSV).
        Logic: sum(w * p for w, p in zip(weights, prob)) / sum(probabilities)
        """
        weighted_score = 0.0
        total_weight = 0.0
        
        for sent, prob in zip(sentiments, probabilities):
            if not prob or len(prob) != len(weights):
                continue
            
            score = sum(w * p for w, p in zip(weights, prob))
            weighted_score += float(score)
            total_weight += float(sum(prob))
            
        if total_weight > 0:
            final_score = weighted_score / total_weight
            return round(final_score, 2)
        return 0.0

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
                # Save to database
                Signal.objects.create(
                    signal_type=signal_type,
                    ticker_id=ticker,
                    confidence_score=score,
                    used_model=used_model,
                    config_ig=config
                )
            
            results[ticker.symbol] = signal_data
            
        return results
