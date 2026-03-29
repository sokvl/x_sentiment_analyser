from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, APIClient

from scraper.models import (
    Config, Source, Content, PostMeta, PostPrediction, Post,
)
from scraper.views.control import ScraperControlView, ScraperLogsView, ScraperConfigView
from tickers.models import Ticker


class ScraperControlViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('scraper.views.control.ScraperService')
    def test_valid_action_start(self, mock_svc_cls):
        mock_svc_cls.return_value.start.return_value = {'message': 'started'}
        view = ScraperControlView.as_view()
        request = self.factory.post('/api/scraper/start/', {'source': 'twitter'})
        response = view(request, action='start')
        self.assertEqual(response.status_code, 200)

    @patch('scraper.views.control.ScraperService')
    def test_invalid_action_returns_400(self, mock_svc_cls):
        view = ScraperControlView.as_view()
        request = self.factory.post('/api/scraper/invalid/', {'source': 'twitter'})
        response = view(request, action='invalid')
        self.assertEqual(response.status_code, 400)

    @patch('scraper.views.control.ScraperService')
    def test_missing_source_returns_400(self, mock_svc_cls):
        view = ScraperControlView.as_view()
        request = self.factory.post('/api/scraper/start/', {})
        response = view(request, action='start')
        self.assertEqual(response.status_code, 400)

    @patch('scraper.views.control.ScraperService')
    def test_service_error_returns_400(self, mock_svc_cls):
        mock_svc_cls.return_value.stop.side_effect = ValueError("Not found")
        view = ScraperControlView.as_view()
        request = self.factory.post('/api/scraper/stop/', {'source': 'unknown'})
        response = view(request, action='stop')
        self.assertEqual(response.status_code, 400)


class ScraperLogsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ScraperLogsView.as_view()

    @patch('scraper.views.control.ScraperService')
    def test_missing_source_returns_400(self, mock_svc_cls):
        request = self.factory.get('/api/scraper/logs/')
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch('scraper.views.control.ScraperService')
    def test_successful_logs(self, mock_svc_cls):
        mock_svc_cls.return_value.logs.return_value = {
            'state': 'running', 'logs': [], 'current_task': {},
        }
        request = self.factory.get('/api/scraper/logs/', {'source': 'twitter'})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    @patch('scraper.views.control.ScraperService')
    def test_scraper_not_running_returns_200_with_defaults(self, mock_svc_cls):
        mock_svc_cls.return_value.logs.side_effect = ValueError("No data")
        request = self.factory.get('/api/scraper/logs/', {'source': 'unknown'})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], 'unknown')


class ConfigViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.config = Config.objects.create(
            name='test_config', active=True,
            config_string={'user_config': {'key': 'val'}, 'scrapers_config': []},
        )

    def test_list_configs(self):
        response = self.client.get('/api/config/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_active_configs(self):
        Config.objects.create(
            name='inactive', active=False,
            config_string={'user_config': {}, 'scrapers_config': []},
        )
        response = self.client.get('/api/config/', {'active': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(c['active'] for c in response.data))

    def test_create_config(self):
        response = self.client.post('/api/config/', {
            'name': 'new_config',
            'active': True,
            'config_string': {'user_config': {}, 'scrapers_config': []},
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_create_config_invalid_config_string(self):
        response = self.client.post('/api/config/', {
            'name': 'bad',
            'active': True,
            'config_string': {'missing_keys': True},
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_update_config_string_action(self):
        response = self.client.patch(
            f'/api/config/{self.config.config_id}/update_config_string/',
            {'config_string': {'user_config': {'new_key': 'new_val'}}},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(self.config.config_string['user_config']['new_key'], 'new_val')
        # Original key should still be there (merge, not replace)
        self.assertEqual(self.config.config_string['user_config']['key'], 'val')

    def test_update_config_string_adds_new_key(self):
        response = self.client.patch(
            f'/api/config/{self.config.config_id}/update_config_string/',
            {'config_string': {'brand_new': 'value'}},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(self.config.config_string['brand_new'], 'value')


class PostViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.content = Content.objects.create(text='Bullish on $AAPL')
        self.meta = PostMeta.objects.create(likes=50)
        self.prediction = PostPrediction.objects.create(
            prediction=2, probabilities=[0.1, 0.2, 0.7], model_name='test',
        )
        self.post = Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=self.ticker,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )

    def test_list_posts(self):
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)

    def test_retrieve_post(self):
        response = self.client.get(f'/api/posts/{self.post.post_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['related_content']['text'], 'Bullish on $AAPL')

    def test_filter_by_ticker_symbol(self):
        response = self.client.get('/api/posts/', {'related_ticker__symbol': 'AAPL'})
        self.assertEqual(response.status_code, 200)

    def test_filter_by_prediction(self):
        response = self.client.get('/api/posts/', {'post_prediction__prediction': 2})
        self.assertEqual(response.status_code, 200)

    def test_post_is_read_only(self):
        response = self.client.post('/api/posts/', {'text': 'new'})
        self.assertEqual(response.status_code, 405)

    def test_delete_not_allowed(self):
        response = self.client.delete(f'/api/posts/{self.post.post_id}/')
        self.assertEqual(response.status_code, 405)


class EvalViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('scraper.views.eval.DataService')
    def test_successful_evaluation(self, mock_ds_cls):
        mock_ds_cls.return_value.evaluate_sentiment.return_value = {
            'text': 'test tweet',
            'ticker': '$AAPL',
            'processed_text': [1, 2, 3, 0, 0],
            'prediction': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
        }
        from scraper.views.eval import EvalView
        view = EvalView.as_view()
        request = self.factory.post('/api/eval/', {
            'tweet': 'test tweet',
            'ticker': '$AAPL',
            'source_name': 'test',
            'date': '2024-01-01',
        })
        response = view(request)
        self.assertEqual(response.status_code, 200)

    @patch('scraper.views.eval.DataService')
    def test_missing_required_fields(self, mock_ds_cls):
        from scraper.views.eval import EvalView
        view = EvalView.as_view()
        request = self.factory.post('/api/eval/', {})
        response = view(request)
        self.assertEqual(response.status_code, 400)
