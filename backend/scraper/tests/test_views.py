from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, APIClient, force_authenticate

from scraper.models import (
    Config, Source, Content, PostMeta, PostPrediction, Post, NewsPost,
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
    def test_scraper_not_found_returns_200_with_idle_state(self, mock_svc_cls):
        mock_svc_cls.return_value.logs.side_effect = ValueError("No data")
        request = self.factory.get('/api/scraper/logs/', {'source': 'unknown'})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], 'IDLE')


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

    def test_update_config_string_rejects_malformed_shape(self):
        # scrapers_config must be a list per ConfigSerializer.validate_config_string —
        # the custom action must not be able to bypass that.
        response = self.client.patch(
            f'/api/config/{self.config.config_id}/update_config_string/',
            {'config_string': {'scrapers_config': 'not-a-list'}},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.config.refresh_from_db()
        self.assertEqual(self.config.config_string['scrapers_config'], [])

    def test_update_config_string_list_merge_does_not_duplicate(self):
        self.config.config_string['scrapers_config'] = [{'crawl_interval': 60}]
        self.config.save()

        for _ in range(3):
            response = self.client.patch(
                f'/api/config/{self.config.config_id}/update_config_string/',
                {'config_string': {'scrapers_config': [{'crawl_interval': 60}]}},
                format='json',
            )
            self.assertEqual(response.status_code, 200)

        self.config.refresh_from_db()
        self.assertEqual(self.config.config_string['scrapers_config'], [{'crawl_interval': 60}])

    def test_update_config_string_list_merge_still_adds_new_items(self):
        self.config.config_string['scrapers_config'] = [{'crawl_interval': 60}]
        self.config.save()

        response = self.client.patch(
            f'/api/config/{self.config.config_id}/update_config_string/',
            {'config_string': {'scrapers_config': [{'crawl_interval': 90}]}},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(
            self.config.config_string['scrapers_config'],
            [{'crawl_interval': 60}, {'crawl_interval': 90}],
        )


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


class AvailableModelsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        from scraper.views.models import AvailableModelsView
        self.view = AvailableModelsView.as_view()

    @patch('scraper.views.models.apps')
    def test_returns_available_and_unavailable_models(self, mock_apps):
        mock_registry = MagicMock()
        mock_registry.available_models = ['FinBERT', 'TweetBERT']
        mock_registry.unavailable_models = ['LSTMCNNv1']
        mock_apps.get_app_config.return_value.MODEL_REGISTRY = mock_registry

        request = self.factory.get('/api/models/')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['available'], ['FinBERT', 'TweetBERT'])
        self.assertEqual(response.data['unavailable'], ['LSTMCNNv1'])

    def test_accessible_without_authentication(self):
        request = self.factory.get('/api/models/')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class NewsPostListViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        from scraper.views.news_post import NewsPostListView
        self.view = NewsPostListView.as_view()

    def _make_news_post(self, symbol='AAPL', headline='Apple news'):
        ticker = Ticker.objects.create(symbol=symbol, type='stock', full_name=symbol)
        prediction = PostPrediction.objects.create(
            prediction=2, probabilities=[0.1, 0.2, 0.7], model_name='FinBERT',
        )
        return NewsPost.objects.create(
            external_id=str(hash((symbol, headline))),
            ticker=ticker,
            headline=headline,
            summary='summary',
            text=f'{headline}. summary',
            url='https://example.com',
            publisher='TheStreet',
            category='company news',
            published_at=timezone.now(),
            news_prediction=prediction,
        )

    def test_empty_db_returns_empty_list(self):
        request = self.factory.get('/api/news/finnhub/')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_returns_saved_news_posts(self):
        self._make_news_post()
        request = self.factory.get('/api/news/finnhub/')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ticker'], 'AAPL')
        self.assertEqual(response.data[0]['prediction'], 2)

    def test_filters_by_tickers_param(self):
        self._make_news_post(symbol='AAPL', headline='Apple news')
        self._make_news_post(symbol='TSLA', headline='Tesla news')
        request = self.factory.get('/api/news/finnhub/', {'tickers': 'AAPL'})
        response = self.view(request)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ticker'], 'AAPL')


@override_settings(RAW_DEBUG=False, INTERVIEWER_ACCESS_KEY='test-key')
class NewsPostListViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        from scraper.views.news_post import NewsPostListView
        self.view = NewsPostListView.as_view()
        self.owner = User.objects.create_user(username='owner', password='pw123456')

    def test_anonymous_no_key_denied(self):
        request = self.factory.get('/api/news/finnhub/')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_interviewer_key_allowed(self):
        request = self.factory.get('/api/news/finnhub/', HTTP_X_ACCESS_KEY='test-key')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_owner_allowed(self):
        request = self.factory.get('/api/news/finnhub/')
        force_authenticate(request, user=self.owner)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class NewsOptimismIndexViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        from scraper.views.news_index import NewsOptimismIndexView
        self.view = NewsOptimismIndexView.as_view()
        self.today = timezone.now().date()

    def _make_news_post(self, symbol, when, probabilities):
        ticker = Ticker.objects.create(symbol=symbol, type='stock', full_name=symbol)
        prediction = PostPrediction.objects.create(
            prediction=2, probabilities=probabilities, model_name='FinBERT',
        )
        return NewsPost.objects.create(
            external_id=str(hash((symbol, when))),
            ticker=ticker,
            headline=f'{symbol} headline',
            summary='summary',
            text=f'{symbol} headline. summary',
            url='https://example.com',
            publisher='TheStreet',
            category='company news',
            published_at=when,
            news_prediction=prediction,
        )

    def test_invalid_start_date_returns_400(self):
        request = self.factory.get('/api/news/finnhub/index/', {'start_date': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_invalid_end_date_returns_400(self):
        request = self.factory.get('/api/news/finnhub/index/', {'end_date': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_start_after_end_returns_400(self):
        request = self.factory.get('/api/news/finnhub/index/', {
            'start_date': '2024-02-01',
            'end_date': '2024-01-01',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_days_with_no_articles_are_omitted(self):
        request = self.factory.get('/api/news/finnhub/index/', {
            'start_date': (self.today - timedelta(days=3)).isoformat(),
            'end_date': self.today.isoformat(),
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['series'], [])

    def test_pools_articles_across_tickers_into_one_daily_score(self):
        self._make_news_post('AAA', timezone.now(), [0.1, 0.2, 0.7])
        self._make_news_post('BBB', timezone.now(), [0.1, 0.2, 0.7])

        request = self.factory.get('/api/news/finnhub/index/', {
            'start_date': self.today.isoformat(),
            'end_date': self.today.isoformat(),
        })
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['series']), 1)
        self.assertEqual(response.data['series'][0]['article_count'], 2)

    def test_defaults_to_full_history_when_no_dates_given(self):
        self._make_news_post('AAA', timezone.now(), [0.1, 0.2, 0.7])

        request = self.factory.get('/api/news/finnhub/index/')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['series']), 1)

    @patch('scraper.views.news_index.NewsOptimismIndexView._build_series')
    def test_internal_error_does_not_leak_exception_text(self, mock_build_series):
        mock_build_series.side_effect = RuntimeError("/etc/secret/db.conf leaked")

        request = self.factory.get('/api/news/finnhub/index/', {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.data['error'])
        self.assertEqual(response.data['error'], 'News index generation failed')


@override_settings(RAW_DEBUG=False, INTERVIEWER_ACCESS_KEY='test-key')
class NewsOptimismIndexViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        from scraper.views.news_index import NewsOptimismIndexView
        self.view = NewsOptimismIndexView.as_view()
        self.owner = User.objects.create_user(username='owner', password='pw123456')

    def test_anonymous_no_key_denied(self):
        request = self.factory.get('/api/news/finnhub/index/')
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_interviewer_key_allowed(self):
        request = self.factory.get('/api/news/finnhub/index/', HTTP_X_ACCESS_KEY='test-key')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_owner_allowed(self):
        request = self.factory.get('/api/news/finnhub/index/')
        force_authenticate(request, user=self.owner)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class EvalViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('scraper.views.eval.DataService')
    def test_successful_evaluation(self, mock_ds_cls):
        mock_ds_cls.return_value.evaluate_sentiment.return_value = {
            'text': 'test tweet',
            'ticker': '$AAPL',
            'cleaned_text': 'test tweet',
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

    @patch('scraper.views.eval.DataService')
    def test_nan_prediction_failure_returns_500(self, mock_ds_cls):
        from rest_framework.exceptions import APIException
        from scraper.views.eval import EvalView

        # Mirrors what DataService.evaluate_sentiment raises when DataManager
        # catches a NaN-producing prediction error and re-raises it as
        # ModelPredictionError: a generic 500 APIException, not a 400.
        mock_ds_cls.return_value.evaluate_sentiment.side_effect = APIException(
            'Unexpected error during evaluation: ',
        )
        view = EvalView.as_view()
        request = self.factory.post('/api/eval/', {
            'tweet': 'test tweet',
            'ticker': '$AAPL',
            'source_name': 'test',
            'date': '2024-01-01',
        })
        response = view(request)
        self.assertEqual(response.status_code, 500)

    @patch('scraper.services.data_service.apps')
    def test_nan_prediction_failure_real_response_body(self, mock_apps):
        # Goes through the REAL DataService + REAL DataManager.eval_sentiment
        # (only the model registry/predictor are mocked), using APIClient so
        # DRF's normal exception-handling/rendering pipeline runs, to show
        # exactly what body/status a client hitting /eval/ gets when the
        # underlying model raises on NaN input.
        from scraper.managers.data_manager.data_manager import DataManager

        mock_registry = MagicMock()
        mock_manager = MagicMock()
        mock_preprocessor = MagicMock()
        mock_registry.get.return_value = (mock_manager, mock_preprocessor, 'transformer_model')
        mock_manager.predict.side_effect = ValueError('cannot convert float NaN to integer')

        real_data_manager = DataManager(model_registry=mock_registry, default_model_id='FinBERT')
        mock_apps.get_app_config.return_value.DATA_MANAGER = real_data_manager

        client = APIClient()
        response = client.post('/api/eval/', {
            'tweet': 'test tweet',
            'ticker': '$AAPL',
            'source_name': 'test',
            'date': '2024-01-01',
        })

        print('\nstatus_code:', response.status_code)
        print('data:', response.data)
        print('content:', response.content)

        self.assertEqual(response.status_code, 500)
