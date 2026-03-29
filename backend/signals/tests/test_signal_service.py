from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase

from signals.services.signal_service import SignalService


class ResolveTickersTests(TestCase):
    def setUp(self):
        self.service = SignalService()

    @patch('signals.services.signal_service.apps')
    def test_resolves_all_tickers(self, mock_apps):
        mock_ticker_cls = MagicMock()
        ticker1, ticker2 = MagicMock(symbol='AAPL'), MagicMock(symbol='TSLA')
        mock_ticker_cls.objects.all.return_value = [ticker1, ticker2]
        mock_apps.get_model.return_value = mock_ticker_cls

        result = self.service.resolve_tickers('all')
        self.assertEqual(result, [ticker1, ticker2])

    @patch('signals.services.signal_service.apps')
    def test_resolves_specific_tickers(self, mock_apps):
        mock_ticker_cls = MagicMock()
        ticker1 = MagicMock(symbol='AAPL')
        mock_ticker_cls.objects.filter.return_value = [ticker1]
        mock_apps.get_model.return_value = mock_ticker_cls

        result = self.service.resolve_tickers('aapl')
        mock_ticker_cls.objects.filter.assert_called_once_with(symbol__in=['AAPL'])
        self.assertEqual(result, [ticker1])

    @patch('signals.services.signal_service.apps')
    def test_resolves_comma_separated_tickers(self, mock_apps):
        mock_ticker_cls = MagicMock()
        mock_ticker_cls.objects.filter.return_value = [MagicMock(), MagicMock()]
        mock_apps.get_model.return_value = mock_ticker_cls

        self.service.resolve_tickers('aapl, tsla')
        mock_ticker_cls.objects.filter.assert_called_once_with(symbol__in=['AAPL', 'TSLA'])

    @patch('signals.services.signal_service.apps')
    def test_raises_when_no_tickers_found(self, mock_apps):
        mock_ticker_cls = MagicMock()
        mock_ticker_cls.objects.filter.return_value = []
        mock_apps.get_model.return_value = mock_ticker_cls

        with self.assertRaises(ValueError):
            self.service.resolve_tickers('UNKNOWN')


class CalculateSentimentScoreTests(TestCase):
    def setUp(self):
        self.service = SignalService()

    def _make_post(self, prediction, probabilities):
        post = MagicMock()
        post.post_prediction.prediction = prediction
        post.post_prediction.probabilities = probabilities
        return post

    def test_returns_zero_for_empty_posts(self):
        self.assertEqual(self.service.calculate_sentiment_score([]), 0.0)

    def test_positive_prediction_returns_positive_score(self):
        post = self._make_post(2, [0.1, 0.2, 0.7])
        score = self.service.calculate_sentiment_score([post])
        self.assertGreater(score, 0)
        self.assertEqual(score, 1.0)

    def test_negative_prediction_returns_negative_score(self):
        post = self._make_post(0, [0.8, 0.1, 0.1])
        score = self.service.calculate_sentiment_score([post])
        self.assertLess(score, 0)
        self.assertEqual(score, -1.0)

    def test_neutral_prediction_contributes_nothing(self):
        post = self._make_post(1, [0.2, 0.6, 0.2])
        score = self.service.calculate_sentiment_score([post])
        self.assertEqual(score, 0.0)

    def test_mixed_predictions(self):
        posts = [
            self._make_post(2, [0.1, 0.2, 0.7]),
            self._make_post(0, [0.6, 0.2, 0.2]),
        ]
        score = self.service.calculate_sentiment_score(posts)
        # weighted_sum = 1.0 * 0.7 + (-1.0 * 0.6) = 0.1
        # total_weight = 0.7 + 0.6 = 1.3
        # score = 0.1 / 1.3 ≈ 0.08
        self.assertAlmostEqual(score, 0.08, places=2)

    def test_skips_posts_with_insufficient_probabilities(self):
        post = self._make_post(2, [0.5])
        score = self.service.calculate_sentiment_score([post])
        self.assertEqual(score, 0.0)

    def test_skips_posts_with_no_probabilities(self):
        post = self._make_post(0, None)
        score = self.service.calculate_sentiment_score([post])
        self.assertEqual(score, 0.0)


class ComputeBatchScoreTests(TestCase):
    def setUp(self):
        self.service = SignalService()

    def test_basic_batch_score(self):
        sentiments = [0, 2]
        probabilities = [[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]]
        weights = [-1, -0.01, 1]
        score = self.service.compute_batch_score(sentiments, probabilities, weights)
        # Row 0: -1*0.7 + -0.01*0.2 + 1*0.1 = -0.602
        # Row 1: -1*0.1 + -0.01*0.2 + 1*0.7 = 0.598
        # weighted_score = -0.602 + 0.598 = -0.004
        # total_weight = 1.0 + 1.0 = 2.0
        # final = -0.004 / 2.0 = -0.002 → rounded to 0.0
        self.assertAlmostEqual(score, 0.0, places=2)

    def test_returns_zero_for_empty_input(self):
        score = self.service.compute_batch_score([], [], [-1, 0, 1])
        self.assertEqual(score, 0.0)

    def test_skips_mismatched_probability_lengths(self):
        sentiments = [0]
        probabilities = [[0.5, 0.5]]  # length 2, weights length 3
        weights = [-1, 0, 1]
        score = self.service.compute_batch_score(sentiments, probabilities, weights)
        self.assertEqual(score, 0.0)


class DetermineSignalTypeTests(TestCase):
    def setUp(self):
        self.service = SignalService()

    def test_buy_signal(self):
        self.assertEqual(self.service.determine_signal_type(0.5), 'BUY')

    def test_sell_signal(self):
        self.assertEqual(self.service.determine_signal_type(-0.5), 'SELL')

    def test_hold_signal(self):
        self.assertEqual(self.service.determine_signal_type(0.0), 'HOLD')

    def test_buy_at_threshold(self):
        self.assertEqual(self.service.determine_signal_type(0.1), 'BUY')

    def test_sell_at_threshold(self):
        self.assertEqual(self.service.determine_signal_type(-0.1), 'SELL')

    def test_hold_just_inside_thresholds(self):
        self.assertEqual(self.service.determine_signal_type(0.09), 'HOLD')
        self.assertEqual(self.service.determine_signal_type(-0.09), 'HOLD')


class GenerateForTickersTests(TestCase):
    def setUp(self):
        self.service = SignalService()

    @patch('signals.services.signal_service.Signal')
    @patch('signals.services.signal_service.apps')
    def test_generates_signals_for_tickers(self, mock_apps, mock_signal):
        mock_config = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.objects.get.return_value = mock_config
        mock_apps.get_app_config.return_value.get_model.return_value = mock_config_cls

        mock_post = MagicMock()
        mock_post.post_prediction.prediction = 2
        mock_post.post_prediction.probabilities = [0.1, 0.2, 0.7]
        mock_qs = MagicMock()
        mock_qs.__iter__ = MagicMock(return_value=iter([mock_post]))
        mock_qs.count.return_value = 1
        mock_post_cls = MagicMock()
        mock_post_cls.objects.filter.return_value.select_related.return_value = mock_qs
        mock_apps.get_model.return_value = mock_post_cls

        ticker = MagicMock()
        ticker.symbol = 'AAPL'
        from datetime import date
        results = self.service.generate_for_tickers(
            tickers=[ticker],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            used_model='LSTMCNNv1',
            with_save=False,
            config_id=1,
        )

        self.assertIn('AAPL', results)
        self.assertIn('signal_type', results['AAPL'])
        self.assertIn('confidence_score', results['AAPL'])
        mock_signal.objects.create.assert_not_called()

    @patch('signals.services.signal_service.Signal')
    @patch('signals.services.signal_service.apps')
    def test_saves_signal_when_with_save_true(self, mock_apps, mock_signal):
        mock_config = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.objects.get.return_value = mock_config
        mock_apps.get_app_config.return_value.get_model.return_value = mock_config_cls

        mock_qs = MagicMock()
        mock_qs.__iter__ = MagicMock(return_value=iter([]))
        mock_qs.count.return_value = 0
        mock_post_cls = MagicMock()
        mock_post_cls.objects.filter.return_value.select_related.return_value = mock_qs
        mock_apps.get_model.return_value = mock_post_cls

        ticker = MagicMock()
        ticker.symbol = 'TSLA'
        from datetime import date
        self.service.generate_for_tickers(
            tickers=[ticker],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            used_model='LSTMCNNv1',
            with_save=True,
            config_id=1,
        )
        mock_signal.objects.create.assert_called_once()

    @patch('signals.services.signal_service.apps')
    def test_raises_when_config_not_found(self, mock_apps):
        mock_config_cls = MagicMock()
        mock_config_cls.DoesNotExist = Exception
        mock_config_cls.objects.get.side_effect = mock_config_cls.DoesNotExist
        mock_apps.get_app_config.return_value.get_model.return_value = mock_config_cls

        with self.assertRaises(ValueError):
            self.service.generate_for_tickers(
                tickers=[],
                start_date=MagicMock(),
                end_date=MagicMock(),
                used_model='X',
                with_save=False,
                config_id=999,
            )
