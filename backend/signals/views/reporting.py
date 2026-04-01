import datetime
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from ..services.signal_service import SignalService
from ..utils import parse_date, fetch_historical_data, safe_round

class PredictionReportView(APIView):
    """
    Backtesting report: compare generated signals against actual stock movements.
    Matches the logic provided in the user's snippet.
    """
    def get(self, request):
        tickers_param = request.query_params.get('tickers', 'all')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {'error': 'Both start_date and end_date are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        if not start_date or not end_date:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'error': 'start_date cannot be after end_date.'}, status=status.HTTP_400_BAD_REQUEST)

        service = SignalService()
        try:
            tickers = service.resolve_tickers(tickers_param)
            report = self._generate_report(service, tickers, start_date, end_date)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {'error': 'Report generation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _generate_report(self, service: SignalService, tickers, start_date, end_date) -> dict:
        report = {}
        total_correct = 0
        total_predictions = 0

        for ticker in tickers:
            symbol_key = ticker.symbol
            ticker_correct = 0
            ticker_total = 0
            daily_results = {}

            stock_data = fetch_historical_data(
                ticker.symbol.lstrip('$'),
                start=start_date - datetime.timedelta(days=1),
                end=end_date + datetime.timedelta(days=1),
            )
            if stock_data is None or (hasattr(stock_data, 'empty') and stock_data.empty):
                report[symbol_key] = {'error': 'No stock data available.'}
                continue

            if isinstance(stock_data.columns, pd.MultiIndex):
                symbol = ticker.symbol.lstrip('$')
                if symbol in stock_data.columns.levels[0]:
                    stock_data = stock_data[symbol]

            # Cache posts by date for efficiency
            # Following the user snippet, we look at [day-1, day] for each date
            # So we pre-fetch from start_date - 1 to end_date
            all_posts = service.get_posts_in_range(ticker, start_date - datetime.timedelta(days=1), end_date)
            posts_by_date = {}
            for post in all_posts:
                d = post.time_stamp.date().isoformat()
                posts_by_date.setdefault(d, []).append(post)

            for n in range((end_date - start_date).days + 1):
                single_date = start_date + datetime.timedelta(days=n)
                date_str = single_date.isoformat()
                prev_date_str = (single_date - datetime.timedelta(days=1)).isoformat()

                # Calculate score for [day-1, day]
                day_posts = posts_by_date.get(date_str, []) + posts_by_date.get(prev_date_str, [])
                if not day_posts:
                    daily_results[date_str] = {'error': 'No posts available for this date/range.'}
                    continue

                score = service.calculate_sentiment_score(day_posts)
                signal_type = service.determine_signal_type(score)

                # Get stock change for this date
                day_data = stock_data.loc[stock_data.index.strftime('%Y-%m-%d') == date_str]
                if day_data.empty:
                    daily_results[date_str] = {'error': 'No stock data for this date.'}
                    continue

                try:
                    open_price = float(day_data['Open'].values[0])
                    close_price = float(day_data['Close'].values[0])
                except (KeyError, IndexError) as e:
                    daily_results[date_str] = {'error': f"Missing column: {e}"}
                    continue

                actual_change = round((close_price - open_price) / open_price * 100, 2)
                is_correct = (
                    (signal_type == 'BUY' and actual_change > 0)
                    or (signal_type == 'SELL' and actual_change < 0)
                    or (signal_type == 'HOLD' and abs(actual_change) <= 0.1)
                )

                daily_results[date_str] = {
                    'prediction': signal_type,
                    'sentiment_score': score,
                    'actual_change': actual_change,
                    'tweet_count': len(day_posts),
                    'correct': is_correct,
                }

                if is_correct:
                    ticker_correct += 1
                    total_correct += 1
                ticker_total += 1
                total_predictions += 1

            report[symbol_key] = daily_results
            report[symbol_key]['ticker_accuracy'] = (
                f"{round(ticker_correct / ticker_total * 100, 2)}%"
                if ticker_total > 0 else 'N/A'
            )

        report['overall_accuracy'] = (
            f"{round(total_correct / total_predictions * 100, 2)}%"
            if total_predictions > 0 else 'N/A'
        )
        return report
