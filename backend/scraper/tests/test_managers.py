from unittest.mock import patch, MagicMock

from django.test import TestCase

from scraper.managers.ScraperManager import ScraperManager


class ScraperManagerTests(TestCase):
    def setUp(self):
        self.manager = ScraperManager()

    def test_get_scraper_returns_none_when_empty(self):
        self.assertIsNone(self.manager.get_scraper('twitter'))

    def test_get_scraper_returns_instance(self):
        mock_scraper = MagicMock()
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': None}
        self.assertEqual(self.manager.get_scraper('twitter'), mock_scraper)

    @patch('scraper.managers.ScraperManager.TwitterScraper')
    @patch('scraper.managers.ScraperManager.Thread')
    def test_set_scraper_creates_and_starts_thread(self, mock_thread_cls, mock_scraper_cls):
        mock_scraper = MagicMock()
        mock_scraper_cls.return_value = mock_scraper
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        self.manager.set_scraper('twitter')

        self.assertIn('twitter', self.manager.scrapers)
        mock_thread.start.assert_called_once()

    @patch('scraper.managers.ScraperManager.TwitterScraper')
    @patch('scraper.managers.ScraperManager.Thread')
    def test_set_scraper_does_not_duplicate(self, mock_thread_cls, mock_scraper_cls):
        mock_scraper_cls.return_value = MagicMock()
        mock_thread_cls.return_value = MagicMock()

        self.manager.set_scraper('twitter')
        self.manager.set_scraper('twitter')  # Should not create another

        self.assertEqual(len(self.manager.scrapers), 1)

    @patch('scraper.managers.ScraperManager.TwitterScraper')
    @patch('scraper.managers.ScraperManager.Thread')
    def test_set_scraper_respects_thread_limit(self, mock_thread_cls, mock_scraper_cls):
        # Fill up with alive scraper threads to hit the limit
        for i in range(self.manager.max_scraper_threads):
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = True
            self.manager.scrapers[f'source_{i}'] = {'scraper': MagicMock(), 'thread': mock_thread}

        self.manager.set_scraper('twitter')
        self.assertNotIn('twitter', self.manager.scrapers)

    def test_stop_scraper_preserves_entry(self):
        mock_scraper = MagicMock()
        mock_thread = MagicMock()
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': mock_thread}

        self.manager.stop_scraper('twitter')

        self.assertIn('twitter', self.manager.scrapers)
        self.assertIsNone(self.manager.scrapers['twitter']['thread'])
        mock_scraper.stop.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=10)

    def test_stop_scraper_nonexistent_does_not_raise(self):
        self.manager.stop_scraper('nonexistent')

    @patch.object(ScraperManager, 'stop_scraper')
    @patch.object(ScraperManager, 'set_scraper')
    def test_restart_calls_stop_then_set(self, mock_set, mock_stop):
        self.manager.restart_scraper('twitter')
        mock_stop.assert_called_once_with('twitter')
        mock_set.assert_called_once_with('twitter')

    def test_access_scraper_calls_method(self):
        mock_scraper = MagicMock()
        mock_scraper.get_state.return_value = {'state': 'running'}
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': None}

        result = self.manager.access_scraper('twitter', 'get_state')
        self.assertEqual(result, {'state': 'running'})

    def test_access_scraper_not_found_raises(self):
        with self.assertRaises(ValueError):
            self.manager.access_scraper('unknown', 'method')

    def test_access_scraper_no_method_raises(self):
        mock_scraper = MagicMock(spec=[])
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': None}

        with self.assertRaises(AttributeError):
            self.manager.access_scraper('twitter', 'nonexistent_method')

    def test_find_and_update_config_success(self):
        mock_scraper = MagicMock()
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': None}

        result = self.manager.find_and_update_scraper_config('twitter', {'key': 'val'})
        self.assertTrue(result)
        mock_scraper.update_config.assert_called_once_with({'key': 'val'})

    def test_find_and_update_config_not_found(self):
        result = self.manager.find_and_update_scraper_config('unknown', {})
        self.assertFalse(result)

    def test_find_and_update_config_exception_returns_false(self):
        mock_scraper = MagicMock()
        mock_scraper.update_config.side_effect = Exception("fail")
        self.manager.scrapers['twitter'] = {'scraper': mock_scraper, 'thread': None}

        result = self.manager.find_and_update_scraper_config('twitter', {})
        self.assertFalse(result)
