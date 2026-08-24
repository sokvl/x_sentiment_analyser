from unittest.mock import patch, MagicMock

from django.test import TestCase

from scraper.management.commands.run_finnhub_ingestion import Command


class RunFinnhubIngestionCommandTests(TestCase):
    def setUp(self):
        self.command = Command()
        self.command.stdout = MagicMock()

    @patch('scraper.management.commands.run_finnhub_ingestion.time')
    @patch('scraper.management.commands.run_finnhub_ingestion.FinnhubNewsService')
    @patch('scraper.management.commands.run_finnhub_ingestion.apps')
    def test_skips_cycle_when_no_active_config(self, mock_apps, mock_service_cls, mock_time):
        mock_apps.get_app_config.return_value.get_model.return_value.objects.filter.return_value.first.return_value = None
        mock_time.sleep.side_effect = StopIteration

        with self.assertRaises(StopIteration):
            self.command.handle()

        mock_service_cls.return_value.fetch_and_enqueue.assert_not_called()

    @patch('scraper.management.commands.run_finnhub_ingestion.time')
    @patch('scraper.management.commands.run_finnhub_ingestion.FinnhubNewsService')
    @patch('scraper.management.commands.run_finnhub_ingestion.apps')
    def test_fetches_for_config_tickers(self, mock_apps, mock_service_cls, mock_time):
        mock_config = MagicMock()
        mock_config.config_string = {'user_config': {'tickers': ['AAPL', 'TSLA']}}
        mock_apps.get_app_config.return_value.get_model.return_value.objects.filter.return_value.first.return_value = mock_config
        mock_service_cls.return_value.fetch_and_enqueue.return_value = 5
        mock_time.sleep.side_effect = StopIteration

        with self.assertRaises(StopIteration):
            self.command.handle()

        args = mock_service_cls.return_value.fetch_and_enqueue.call_args[0]
        self.assertEqual(args[0], ['AAPL', 'TSLA'])

    @patch('scraper.management.commands.run_finnhub_ingestion.time')
    @patch('scraper.management.commands.run_finnhub_ingestion.FinnhubNewsService')
    @patch('scraper.management.commands.run_finnhub_ingestion.apps')
    def test_cycle_exception_does_not_crash_loop(self, mock_apps, mock_service_cls, mock_time):
        mock_apps.get_app_config.side_effect = RuntimeError('db unavailable')
        mock_time.sleep.side_effect = StopIteration

        with self.assertRaises(StopIteration):
            self.command.handle()

        mock_time.sleep.assert_called_once()
