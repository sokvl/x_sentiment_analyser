# signals/views.py
from __future__ import annotations

import csv
import datetime
import json
from io import TextIOWrapper

import pandas as pd
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from scraper.models import Post
from stocknlp.tasks import enqueue_user_data
from stocknlp.tasks import redis_client

from .filters import SignalFilter
from .models import Config
from .models import Signal
from .models import Ticker
from .serializers import SignalSerializer
from .utils import fetch_historical_data
from .utils import get_data_manager
from .utils import parse_date
from .utils import safe_round


class SignalListView(generics.ListAPIView):
    """
    Endpoint do pobierania listy sygnałów z filtrowaniem.
    """
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SignalFilter


class ProcessCSVView(APIView):
    """
    Endpoint do przetwarzania pliku CSV zawierającego tweety, generowania predykcji i pobierania danych z yfinance.
    """
    REQUIRED_COLUMNS = ['Date', 'Ticker', 'Tweet']
    BATCH_SIZE = 100
    WEIGHTS = [-1, -0.01, 1]

    def post(self, request):
        file = request.FILES.get('file')
        if not self.is_valid_file(file):
            return self.invalid_file_response()

        data_manager, error = get_data_manager()
        if not data_manager:
            return self.data_manager_error_response(error)

        try:
            reader = self.get_csv_reader(file)
            if not self.has_required_columns(reader.fieldnames):
                missing = self.get_missing_columns(reader.fieldnames)
                return self.missing_columns_response(missing)

            results, errors = self.process_csv(reader, data_manager)
            self.calculate_sentiment_scores(results)
            self.add_yfinance_data(results, errors)

            return Response({'results': results, 'errors': errors}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.processing_error_response(e)

    def is_valid_file(self, file):
        is_valid = file and file.name.endswith('.csv')
        return is_valid

    def invalid_file_response(self):
        return Response(
            {'error': 'Invalid file format. Please upload a CSV file.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def data_manager_error_response(self, details):
        return Response(
            {'error': 'DataManager not initialized', 'details': details},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def get_csv_reader(self, file):
        csv_file = TextIOWrapper(file, encoding='utf-8')
        reader = csv.DictReader(csv_file)
        return reader

    def has_required_columns(self, fieldnames):
        has_columns = all(col in fieldnames for col in self.REQUIRED_COLUMNS)
        return has_columns

    def get_missing_columns(self, fieldnames):
        missing = [col for col in self.REQUIRED_COLUMNS if col not in fieldnames]
        return missing

    def missing_columns_response(self, missing):
        return Response(
            {'error': f"Missing columns: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def processing_error_response(self, error):
        return Response(
            {
                'error': 'Error reading or processing CSV file',
                'details': str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def process_csv(self, reader, data_manager):
        results = {}
        errors = []
        batch = []
        row_count = 0

        for i, row in enumerate(reader, start=1):
            row_count += 1
            tweet_data, parse_error = self.parse_row(row)
            if parse_error:
                errors.append({'row': i, 'details': parse_error, 'data': row})
                continue

            batch.append(tweet_data)
            if len(batch) >= self.BATCH_SIZE:
                self.process_batch(batch, data_manager, results, errors)
                batch = []

        if batch:
            self.process_batch(batch, data_manager, results, errors)

        return results, errors

    def parse_row(self, row):
        try:
            tweet_date = parse_date(row['Date'])
            if not tweet_date:
                raise ValueError('Invalid date format.')
            tweet_data = {
                'text': row['Tweet'],
                'ticker': f"${row['Ticker']}",
                'source_name': 'CSV Upload',
                'date': tweet_date,
            }
            return tweet_data, None
        except ValueError as e:
            return None, str(e)

    def get_result(self, request_id, timeout=30):
        result = redis_client.brpop(
            f'response_queue:{request_id}', timeout=timeout,
        )
        if result:
            _, data = result
            return json.loads(data)
        else:
            return {'status': 'timeout'}

    def process_batch(self, batch, data_manager, results, errors):
        request_ids = []

        for tweet_data in batch:
            try:
                request_id = enqueue_user_data(tweet_data)
                request_ids.append((request_id, tweet_data))
            except Exception as e:
                errors.append(
                    {
                        'details': f"Error queuing tweet: {str(e)}",
                        'data': tweet_data,
                    },
                )

        for request_id, tweet_data in request_ids:
            try:
                result = self.get_result(request_id, timeout=30)
                if result.get('status') == 'timeout':
                    raise Exception('Timeout: Result not received in time')

                date_str = tweet_data['date'].strftime('%Y-%m-%d')
                ticker = tweet_data['ticker']

                ticker_data = results.setdefault(ticker, {}).setdefault(
                    date_str, {
                        'sentiments': [],
                        'probabilities': [],
                    },
                )

                ticker_data['sentiments'].append(result['prediction'])
                ticker_data['probabilities'].append(
                    result['predicted_probabilities'],
                )

            except Exception as e:
                errors.append(
                    {'details': f"Error receiving tweet result: {str(e)}", 'data': tweet_data},
                )

    def calculate_sentiment_scores(self, results):
        for ticker, dates in results.items():
            for date, data in dates.items():
                sentiments = data.pop('sentiments', [])
                probabilities = data.pop('probabilities', [])

                if not sentiments or not probabilities:
                    data['sentiment_score'] = 0
                    continue

                weighted_score, total_weight = self.compute_weighted_score(
                    sentiments, probabilities,
                )
                sentiment_score = round(
                    weighted_score / total_weight, 2,
                ) if total_weight > 0 else 0
                data['sentiment_score'] = sentiment_score

    def compute_weighted_score(self, sentiments, probabilities):
        weighted_score = 0
        total_weight = 0
        for sentiment, prob in zip(sentiments, probabilities):
            if len(prob) != len(self.WEIGHTS):
                continue

            score = sum(w * p for w, p in zip(self.WEIGHTS, prob))
            weighted_score += score
            total_weight += sum(prob)

        return weighted_score, total_weight

    def add_yfinance_data(self, results, errors):
        tickers = [ticker.lstrip('$') for ticker in results.keys()]
        try:
            historical_data = fetch_historical_data(','.join(tickers))
            for ticker, dates in results.items():
                self.add_stock_data_to_ticker(
                    ticker.lstrip(
                        '$',
                    ), dates, historical_data, errors,
                )
        except Exception as e:
            errors.append(
                {'details': f"Error fetching yfinance data: {str(e)}"},
            )

    def add_stock_data_to_ticker(self, ticker, dates, historical_data, errors):
        ticker_history = historical_data.get(ticker)
        if ticker_history is None:
            for date in dates:
                dates[date]['stock_data'] = {
                    'error': f"No historical data available for {ticker}.",
                }
            return

        for date in dates:
            try:
                day_data = ticker_history.loc[
                    ticker_history.index.strftime(
                        '%Y-%m-%d',
                    ) == date
                ]
                if not day_data.empty:
                    day_record = day_data.iloc[0]
                    dates[date]['stock_data'] = {
                        'Open': safe_round(day_record['Open']),
                        'Close': safe_round(day_record['Close']),
                        'minDay': safe_round(day_record['Low']),
                        'maxDay': safe_round(day_record['High']),
                    }
                else:
                    dates[date]['stock_data'] = {
                        'error': 'No stock data for this date.',
                    }
            except Exception as e:
                errors.append(
                    {'details': f"Error processing stock data for {ticker} on {date}: {str(e)}"},
                )


class SignalGenerationView(APIView):
    def get(self, request):
        params = self.get_params(request)
        validation_error, parsed_date = self.validate_params(params)
        if validation_error:
            return validation_error

        params['date'] = parsed_date
        tickers = self.get_tickers(params)
        if not tickers.exists():
            return self.no_tickers_found_response()

        results = []
        for ticker in tickers:
            sentiment_score = self.calculate_ratio(ticker, params['date'])
            signal_type = self.determine_signal_type(sentiment_score)
            if params['with_save']:
                self.save_signal(
                    ticker, sentiment_score,
                    signal_type, params, 1,
                )

            results.append({
                'ticker': ticker.symbol,
                'sentiment_score': sentiment_score,
                'signal_type': signal_type,
                'used_model': params['used_model'],
                'config_id': 1,
                'saved': params['with_save'],
            })

        return Response(results, status=status.HTTP_200_OK)

    def get_params(self, request):
        return {
            'date': request.query_params.get('date'),
            'tickers': request.query_params.get('tickers', 'all'),
            'used_model': request.query_params.get('used_model', 'LSTMCNNv1'),
            'config_id': request.query_params.get('config_id', 1),
            'with_save': request.query_params.get('with_save', 'false').lower() == 'true',
        }

    def validate_params(self, params):
        if not params['date']:
            return Response({'error': 'Date parameter is required.'}, status=status.HTTP_400_BAD_REQUEST), None
        parsed_date = parse_date(params['date'])
        if not parsed_date:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST), None
        return None, parsed_date

    def get_config(self, config_id):
        return Config.objects.filter(config_id=config_id).first()

    def config_not_found_response(self, config_id):
        return Response(
            {'error': f"Config with ID {config_id} not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    def get_tickers(self, params):
        if params['tickers'] == 'all':
            return Ticker.objects.all()
        ticker_symbols = params['tickers'].split(',')
        return Ticker.objects.filter(symbol__in=ticker_symbols)

    def no_tickers_found_response(self):
        return Response(
            {'error': 'No valid tickers found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    def determine_signal_type(self, sentiment_score):
        if sentiment_score > 0.1:
            return 'BUY'
        elif sentiment_score < -0.1:
            return 'SELL'
        else:
            return 'HOLD'

    def save_signal(self, ticker, sentiment_score, signal_type, params, config):
        Signal.objects.create(
            signal_type=signal_type,
            ticker_id=ticker,
            confidence_score=sentiment_score,
            generated_at=now(),
            used_model=params['used_model'],
            config_ig=config,
        )

    def calculate_ratio(self, ticker, date):
        previous_day = date - datetime.timedelta(days=1)
        posts = Post.objects.filter(
            related_ticker=ticker,
            # Poprawka: Usunięto '__date__'
            time_stamp__in=[previous_day, date],
        ).select_related('post_prediction')

        weighted_sum, total_weight = 0, 0
        for post in posts:
            prediction = post.post_prediction.prediction
            # Lista P(0), P(1), P(2)
            probabilities = post.post_prediction.probabilities

            weight_0 = probabilities[0] if len(probabilities) > 0 else 0
            weight_2 = probabilities[2] if len(probabilities) > 2 else 0

            if prediction == 0:
                weighted_sum += -1 * weight_0
                total_weight += weight_0
            elif prediction == 2:
                weighted_sum += 1 * weight_2
                total_weight += weight_2

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 2)


class PredictionReportView(APIView):
    def get(self, request):
        tickers_param = request.query_params.get('tickers', 'all')
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')

        if not start_date_param or not end_date_param:
            return Response({'error': 'Both start_date and end_date parameters are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = parse_date(start_date_param)
            end_date = parse_date(end_date_param)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'error': 'start_date cannot be after end_date.'}, status=status.HTTP_400_BAD_REQUEST)

        if tickers_param == 'all':
            tickers = Ticker.objects.all()
        else:
            ticker_symbols = tickers_param.split(',')
            print(ticker_symbols)
            tickers = Ticker.objects.filter(symbol__in=ticker_symbols)

        if not tickers.exists():
            return Response({'error': 'No valid tickers found.'}, status=status.HTTP_404_NOT_FOUND)

        report_data = self.generate_report(tickers, start_date, end_date)
        return Response(report_data, status=status.HTTP_200_OK)

    def generate_report(self, tickers, start_date, end_date):
        report_result = {}
        total_correct = 0
        total_predictions = 0

        for ticker in tickers:
            report_result[ticker.symbol] = {}

            stock_data = fetch_historical_data(ticker.symbol.lstrip('$'))

            if stock_data.empty:
                report_result[ticker.symbol] = {
                    'error': 'No stock data available for the last 10 years.',
                }
                continue

            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data = stock_data.xs(ticker.symbol.lstrip('$'), axis=1)

            for single_date in self._date_range(start_date, end_date):
                posts = Post.objects.filter(
                    related_ticker=ticker,
                    time_stamp__range=[
                        single_date -
                        datetime.timedelta(days=1), single_date,
                    ],
                )

                if posts.count() == 0:
                    report_result[ticker.symbol][str(single_date)] = {
                        'error': 'No posts available for this date.',
                    }
                    continue

                daily_sentiment_score = self._calculate_sentiment_score(posts)

                day_stock_data = stock_data.loc[
                    stock_data.index.strftime(
                        '%Y-%m-%d',
                    ) == single_date.strftime('%Y-%m-%d')
                ]
                if day_stock_data.empty:
                    report_result[ticker.symbol][str(single_date)] = {
                        'error': 'No stock data available for this date.',
                    }
                    continue

                try:
                    open_price = day_stock_data['Open'].values[0].item()
                    close_price = day_stock_data['Close'].values[0].item()
                except KeyError as e:
                    report_result[ticker.symbol][str(single_date)] = {
                        'error': f"Missing column: {e}",
                    }
                    continue

                actual_change = round(
                    (close_price - open_price) / open_price * 100, 2,
                )

                sentiment_type = 'BUY' if daily_sentiment_score > 0.1 else 'SELL' if daily_sentiment_score < -0.1 else 'HOLD'
                is_correct = (sentiment_type == 'BUY' and actual_change > 0) or \
                             (sentiment_type == 'SELL' and actual_change < 0) or \
                             (sentiment_type == 'HOLD' and abs(actual_change) <= 0.1)

                report_result[ticker.symbol][str(single_date)] = {
                    'prediction': sentiment_type,
                    'actual_change': actual_change,
                    'tweet_count': posts.count(),
                    'correct': is_correct,
                }

                if is_correct:
                    total_correct += 1
                total_predictions += 1

            if total_predictions > 0:
                report_result[ticker.symbol][
                    'ticker_total_correctness'
                ] = f"{round(total_correct / total_predictions * 100, 2)}%"
            else:
                report_result[ticker.symbol][
                    'ticker_total_correctness'
                ] = 'N/A (No predictions)'

        if total_predictions > 0:
            report_result['total_correct'] = f"{round(total_correct / total_predictions * 100, 2)}%"
        else:
            report_result['total_correct'] = 'N/A (No predictions)'

        return report_result

    def _calculate_sentiment_score(self, posts):
        """
        Oblicza sentiment score na podstawie postów.
        """
        weighted_sum = 0
        total_weight = 0

        for post in posts:
            prediction = post.post_prediction.prediction
            probabilities = post.post_prediction.probabilities

            weight_0 = probabilities[0] if len(probabilities) > 0 else 0
            weight_2 = probabilities[2] if len(probabilities) > 2 else 0

            if prediction == 0:
                weighted_sum += -1 * weight_0
                total_weight += weight_0
            elif prediction == 2:
                weighted_sum += 1 * weight_2
                total_weight += weight_2

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 2)

    def _date_range(self, start_date, end_date):
        """
        Generator zwracający kolejne dni z podanego zakresu dat.
        """
        for n in range((end_date - start_date).days + 1):
            yield start_date + datetime.timedelta(n)
