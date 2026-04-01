from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase

from scraper.services.scraper_service import ScraperService


class ScraperServiceTests(TestCase):
    @patch('scraper.services.scraper_service.apps')
    def setUp(self, mock_apps):
        self.mock_manager = MagicMock()
        mock_apps.get_app_config.return_value.SCRAPER_MANAGER = self.mock_manager
        self.service = ScraperService()

    def test_start_creates_scraper_if_not_exists(self):
        self.mock_manager.get_scraper.return_value = None
        result = self.service.start('twitter')
        self.mock_manager.set_scraper.assert_called_once_with('twitter')
        self.assertIn('message', result)

    def test_start_does_not_create_if_exists(self):
        self.mock_manager.get_scraper.return_value = MagicMock()
        result = self.service.start('twitter')
        self.mock_manager.set_scraper.assert_not_called()
        self.assertIn('message', result)

    def test_pause_success(self):
        self.mock_manager.get_scraper.return_value = MagicMock()
        self.mock_manager.access_scraper.return_value = True
        result = self.service.pause('twitter')
        self.assertIn('paused', result['message'])

    def test_pause_scraper_not_found_raises(self):
        self.mock_manager.get_scraper.return_value = None
        with self.assertRaises(ValueError):
            self.service.pause('unknown')

    def test_resume_success(self):
        self.mock_manager.get_scraper.return_value = MagicMock()
        self.mock_manager.access_scraper.return_value = True
        result = self.service.resume('twitter')
        self.assertIn('resumed', result['message'])

    def test_resume_not_found_raises(self):
        self.mock_manager.get_scraper.return_value = None
        with self.assertRaises(ValueError):
            self.service.resume('unknown')

    def test_stop_success(self):
        self.mock_manager.get_scraper.return_value = MagicMock()
        result = self.service.stop('twitter')
        self.mock_manager.stop_scraper.assert_called_once_with('twitter')
        self.assertIn('stopped', result['message'])

    def test_stop_not_found_raises(self):
        self.mock_manager.get_scraper.return_value = None
        with self.assertRaises(ValueError):
            self.service.stop('unknown')

    def test_restart_success(self):
        self.mock_manager.get_scraper.return_value = MagicMock()
        result = self.service.restart('twitter')
        self.mock_manager.restart_scraper.assert_called_once_with('twitter')
        self.assertIn('restarted', result['message'])

    def test_restart_not_found_raises(self):
        self.mock_manager.get_scraper.return_value = None
        with self.assertRaises(ValueError):
            self.service.restart('unknown')

    def test_logs_success(self):
        self.mock_manager.access_scraper.return_value = {
            'state': 'running',
            'logs': ['log1', 'log2'],
            'current_task_details': {'id': 1},
        }
        result = self.service.logs('twitter')
        self.assertEqual(result['state'], 'running')
        self.assertEqual(len(result['logs']), 2)

    def test_logs_no_data_raises(self):
        self.mock_manager.access_scraper.return_value = None
        with self.assertRaises(ValueError):
            self.service.logs('twitter')

    def test_update_config_success(self):
        self.mock_manager.find_and_update_scraper_config.return_value = True
        result = self.service.update_config({'source': 'twitter', 'key': 'value'})
        self.assertIn('updated', result['message'].lower())

    def test_update_config_not_found_raises(self):
        self.mock_manager.find_and_update_scraper_config.return_value = False
        with self.assertRaises(ValueError):
            self.service.update_config({'source': 'unknown'})
