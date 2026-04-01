import csv
import io
import json
import logging
from typing import List, Dict, Any, Tuple, Union
import pandas as pd
from django.utils import timezone
from django.conf import settings
from .signal_service import SignalService
from ..utils import safe_round, parse_date, fetch_historical_data
from ..constants import CSV_BATCH_SIZE, SENTIMENT_WEIGHTS
from stocknlp.tasks import enqueue_user_data, get_redis

logger = logging.getLogger(__name__)

class CSVProcessingService:
    """
    Service for processing uploaded CSV files containing tweets for sentiment evaluation.
    """

    REQUIRED_COLUMNS = ['Date', 'Ticker', 'Tweet']

    def __init__(self):
        self.signal_service = SignalService()
        self.redis_client = get_redis()

    def process(self, file_obj: Any, model_id: str | None = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parses the CSV file and evaluates sentiment for each row using Redis tasks.
        Returns a tuple of (results, errors).
        """
        results: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []
        batch: List[Dict[str, Any]] = []

        try:
            content = file_obj.read().decode('utf-8')
            logger.debug('CSV content length: %d characters', len(content))
            csv_reader = csv.DictReader(io.StringIO(content))

            fieldnames = csv_reader.fieldnames or []
            logger.debug('Found fieldnames: %s', fieldnames)

            if not all(col in fieldnames for col in self.REQUIRED_COLUMNS):
                missing = [col for col in self.REQUIRED_COLUMNS if col not in fieldnames]
                logger.error('Missing columns: %s', missing)
                raise ValueError(f"Missing required columns: {', '.join(missing)}")

            for row_idx, row in enumerate(csv_reader, start=1):
                parsed_data, error = self._parse_row(row)
                if error or parsed_data is None:
                    logger.debug('Row %d parse error: %s', row_idx, error)
                    errors.append({'row': row_idx, 'details': error or "Parsing failed", 'data': row})
                    continue

                batch.append(parsed_data)
                if len(batch) >= CSV_BATCH_SIZE:
                    logger.debug('Processing batch of size %d. Total processed rows: %d', len(batch), row_idx)
                    self._process_batch(batch, results, errors, model_id)
                    batch = []

            if batch:
                logger.debug('Processing final batch of size %d', len(batch))
                self._process_batch(batch, results, errors, model_id)

            self._calculate_scores(results)
            self._add_yfinance_data(results, errors)

        except Exception:
            logger.exception("CSV processing failed")
            raise

        return results, errors

    def _parse_row(self, row: Dict[str, str]) -> Tuple[Union[Dict[str, Any], None], Union[str, None]]:
        try:
            tweet_date = parse_date(row['Date'])
            if not tweet_date:
                raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

            tweet_data = {
                'text': row['Tweet'],
                'ticker': f"${row['Ticker']}" if not row['Ticker'].startswith('$') else row['Ticker'],
                'source_name': 'CSV Upload',
                'date': tweet_date,
            }
            return tweet_data, None
        except Exception as e:
            return None, str(e)

    def _process_batch(self, batch: List[Dict[str, Any]], results: Dict[str, Any], errors: List[Dict[str, Any]], model_id: str | None):
        request_ids = []

        logger.debug('Enqueuing %d tweets for evaluation', len(batch))
        for tweet_data in batch:
            try:
                if model_id:
                    tweet_data['model_id'] = model_id
                request_id = enqueue_user_data(tweet_data)
                request_ids.append((request_id, tweet_data))
            except Exception as e:
                logger.error('Failed to enqueue tweet: %s', e)
                errors.append({'details': f"Error queuing tweet: {e}", 'data': tweet_data})

        logger.debug('Waiting for %d results from Redis', len(request_ids))
        for request_id, tweet_data in request_ids:
            try:
                result_raw = self.redis_client.brpop(f'response_queue:{request_id}', timeout=30)
                if not result_raw:
                    logger.error('Timeout waiting for request_id: %s', request_id)
                    raise Exception("Timeout: Result not received from worker in 30s")

                _, data = result_raw
                result = json.loads(data)

                date_str = tweet_data['date'].strftime('%Y-%m-%d')
                ticker = tweet_data['ticker']

                logger.debug('Received result for %s on %s: %s', ticker, date_str, result.get('prediction'))

                ticker_data = results.setdefault(ticker, {}).setdefault(date_str, {
                    'probabilities': [],
                })

                ticker_data['probabilities'].append(result['predicted_probabilities'])

            except Exception as e:
                logger.error('Exception while receiving results: %s', e)
                errors.append({'details': f"Error receiving tweet result: {e}", 'data': tweet_data})

    def _calculate_scores(self, results: Dict[str, Any]):
        logger.debug('Calculating final scores for %d tickers', len(results))
        for ticker, dates in results.items():
            for date_str, data in dates.items():
                probabilities = data.pop('probabilities', [])

                if not probabilities:
                    logger.debug('No data for %s on %s, skipping score calculation', ticker, date_str)
                    data['sentiment_score'] = 0.0
                    continue

                data['sentiment_score'] = self.signal_service.compute_batch_score(
                    probabilities, SENTIMENT_WEIGHTS,
                )
                logger.debug('Final score for %s on %s: %s', ticker, date_str, data['sentiment_score'])

    def _add_yfinance_data(self, results: Dict[str, Any], errors: List[Dict[str, Any]]):
        symbols = [s.lstrip('$') for s in results.keys()]
        if not symbols:
            return

        try:
            historical_data = fetch_historical_data(','.join(symbols))
            if historical_data is None or (hasattr(historical_data, 'empty') and historical_data.empty):
                for ticker, dates in results.items():
                    for date_str, data in dates.items():
                        data['stock_data'] = {'error': 'No historical data available.'}
                return

            for ticker, dates in results.items():
                symbol = ticker.lstrip('$')
                ticker_history = None
                if isinstance(historical_data.columns, pd.MultiIndex):
                    if symbol in historical_data.columns.levels[0]:
                        ticker_history = historical_data[symbol]
                else:
                    ticker_history = historical_data

                for date_str, data in dates.items():
                    if ticker_history is None or ticker_history.empty:
                         data['stock_data'] = {'error': f"No historical data available for {symbol}."}
                         continue

                    try:
                        day_data = ticker_history.loc[ticker_history.index.strftime('%Y-%m-%d') == date_str]
                        if not day_data.empty:
                            row = day_data.iloc[0]
                            data['stock_data'] = {
                                'Open': safe_round(row['Open']),
                                'Close': safe_round(row['Close']),
                                'minDay': safe_round(row['Low']),
                                'maxDay': safe_round(row['High']),
                            }
                        else:
                            data['stock_data'] = {'error': 'No stock data for this date.'}
                    except Exception as e:
                        errors.append({'details': f"Error processing stock data for {symbol} on {date_str}: {e}"})
        except Exception as e:
            errors.append({'details': f"Error fetching yfinance data: {e}"})
