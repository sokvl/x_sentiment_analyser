from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, APIClient, force_authenticate

from stocknlp.models import InterviewerKey
from tickers.models import Ticker
from tickers.views.ticker import TickerViewSet
from tickers.views.stock_data import StockDataView
from tickers.views.ticker_news import TickerNewsView


class TickerViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )

    def test_list_tickers(self):
        response = self.client.get('/api/tickers/tickers/')
        self.assertEqual(response.status_code, 200)

    def test_retrieve_ticker(self):
        response = self.client.get(f'/api/tickers/tickers/{self.ticker.ticker_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['symbol'], 'AAPL')

    def test_create_ticker(self):
        response = self.client.post('/api/tickers/tickers/', {
            'symbol': 'TSLA',
            'type': 'stock',
            'full_name': 'Tesla Inc.',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticker.objects.count(), 2)

    def test_create_bulk_tickers(self):
        response = self.client.post(
            '/api/tickers/tickers/',
            [
                {'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'},
                {'symbol': 'MSFT', 'type': 'stock', 'full_name': 'Microsoft Corp.'},
            ],
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticker.objects.count(), 3)

    def test_search_tickers(self):
        Ticker.objects.create(symbol='TSLA', type='stock', full_name='Tesla Inc.')
        response = self.client.get('/api/tickers/tickers/', {'search': 'Apple'})
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        symbols = [t['symbol'] for t in results]
        self.assertIn('AAPL', symbols)

    def test_filter_by_type(self):
        Ticker.objects.create(symbol='BTC', type='crypto', full_name='Bitcoin')
        response = self.client.get('/api/tickers/tickers/', {'type': 'crypto'})
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertTrue(all(t['type'] == 'crypto' for t in results))

    def test_list_by_type_action(self):
        Ticker.objects.create(symbol='BTC', type='crypto', full_name='Bitcoin')
        response = self.client.get('/api/tickers/tickers/by-type/crypto/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(t['type'] == 'crypto' for t in response.data))

    def test_delete_ticker(self):
        response = self.client.delete(f'/api/tickers/tickers/{self.ticker.ticker_id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Ticker.objects.count(), 0)

    def test_update_ticker(self):
        response = self.client.patch(
            f'/api/tickers/tickers/{self.ticker.ticker_id}/',
            {'full_name': 'Apple Corporation'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.ticker.refresh_from_db()
        self.assertEqual(self.ticker.full_name, 'Apple Corporation')


@override_settings(RAW_DEBUG=False)
class TickerViewSetPermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pw123456')
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.interviewer_client = APIClient()
        _, raw_key = InterviewerKey.create_key(label='test')
        self.interviewer_headers = {'HTTP_X_ACCESS_KEY': raw_key}

        self.anon_client = APIClient()

        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.',
        )

    def test_anonymous_list_retrieve_by_type_succeed(self):
        self.assertEqual(self.anon_client.get('/api/tickers/tickers/').status_code, 200)
        self.assertEqual(
            self.anon_client.get(f'/api/tickers/tickers/{self.ticker.ticker_id}/').status_code, 200,
        )
        self.assertEqual(
            self.anon_client.get('/api/tickers/tickers/by-type/stock/').status_code, 200,
        )

    def test_interviewer_create_denied(self):
        response = self.interviewer_client.post(
            '/api/tickers/tickers/',
            {'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'},
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_interviewer_bulk_create_denied(self):
        response = self.interviewer_client.post(
            '/api/tickers/tickers/',
            [{'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'}],
            format='json',
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_interviewer_update_denied(self):
        response = self.interviewer_client.patch(
            f'/api/tickers/tickers/{self.ticker.ticker_id}/',
            {'full_name': 'x'}, format='json',
            **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_interviewer_destroy_denied(self):
        response = self.interviewer_client.delete(
            f'/api/tickers/tickers/{self.ticker.ticker_id}/', **self.interviewer_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_create_allowed(self):
        response = self.owner_client.post(
            '/api/tickers/tickers/',
            {'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'},
        )
        self.assertEqual(response.status_code, 201)

    def test_owner_bulk_create_allowed(self):
        response = self.owner_client.post(
            '/api/tickers/tickers/',
            [{'symbol': 'TSLA', 'type': 'stock', 'full_name': 'Tesla Inc.'}],
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    @override_settings(MAX_TICKER_BULK_CREATE=2)
    def test_owner_bulk_create_over_limit_rejected(self):
        payload = [
            {'symbol': f'SYM{i}', 'type': 'stock', 'full_name': f'Symbol {i}'}
            for i in range(3)
        ]
        response = self.owner_client.post('/api/tickers/tickers/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ticker.objects.count(), 1)

    @override_settings(MAX_TICKER_BULK_CREATE=2)
    def test_owner_bulk_create_at_limit_allowed(self):
        payload = [
            {'symbol': f'SYM{i}', 'type': 'stock', 'full_name': f'Symbol {i}'}
            for i in range(2)
        ]
        response = self.owner_client.post('/api/tickers/tickers/', payload, format='json')
        self.assertEqual(response.status_code, 201)

    def test_owner_update_allowed(self):
        response = self.owner_client.patch(
            f'/api/tickers/tickers/{self.ticker.ticker_id}/',
            {'full_name': 'Apple Corporation'}, format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_owner_destroy_allowed(self):
        response = self.owner_client.delete(f'/api/tickers/tickers/{self.ticker.ticker_id}/')
        self.assertEqual(response.status_code, 204)


class StockDataViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = StockDataView.as_view()
        Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple Inc.')

    @patch('tickers.views.stock_data.TickerService')
    def test_successful_stock_data_fetch(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_date_range.return_value = (MagicMock(), MagicMock())
        mock_service.fetch_stock_data.return_value = {'AAPL': [{'Open': 150}]}

        request = self.factory.get('/api/tickers/stock-data/', {
            'tickers': 'AAPL',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('AAPL', response.data)

    @patch('tickers.views.stock_data.TickerService')
    def test_not_found_returns_404(self, mock_service_cls):
        from rest_framework.exceptions import NotFound
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.side_effect = NotFound("No valid tickers")

        request = self.factory.get('/api/tickers/stock-data/')
        response = self.view(request)
        self.assertEqual(response.status_code, 404)

    @patch('tickers.views.stock_data.TickerService')
    def test_validation_error_returns_400(self, mock_service_cls):
        from rest_framework.exceptions import ValidationError
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_date_range.side_effect = ValidationError("Invalid date format")

        request = self.factory.get('/api/tickers/stock-data/', {'tickers': 'AAPL', 'start_date': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)


@override_settings(RAW_DEBUG=False)
class StockDataViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = StockDataView.as_view()
        self.owner = User.objects.create_user(username='owner', password='pw123456')
        _, self.raw_key = InterviewerKey.create_key(label='test')

    def test_anonymous_no_key_denied(self):
        request = self.factory.get('/api/tickers/stock-data/', {'tickers': 'AAPL'})
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    @patch('tickers.views.stock_data.TickerService')
    def test_interviewer_key_allowed(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_date_range.return_value = (MagicMock(), MagicMock())
        mock_service.fetch_stock_data.return_value = {'AAPL': [{'Open': 150}]}

        request = self.factory.get(
            '/api/tickers/stock-data/', {'tickers': 'AAPL'}, HTTP_X_ACCESS_KEY=self.raw_key,
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    @patch('tickers.views.stock_data.TickerService')
    def test_owner_allowed(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_date_range.return_value = (MagicMock(), MagicMock())
        mock_service.fetch_stock_data.return_value = {'AAPL': [{'Open': 150}]}

        request = self.factory.get('/api/tickers/stock-data/', {'tickers': 'AAPL'})
        force_authenticate(request, user=self.owner)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class TickerNewsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TickerNewsView.as_view()
        Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple Inc.')

    @patch('tickers.views.ticker_news.TickerService')
    def test_successful_news_fetch(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_news_count.return_value = 5
        mock_service.fetch_news.return_value = {'AAPL': [{'title': 'Apple news'}]}

        request = self.factory.get('/api/tickers/news/', {'tickers': 'AAPL'})
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('AAPL', response.data)

    @patch('tickers.views.ticker_news.TickerService')
    def test_not_found_returns_404(self, mock_service_cls):
        from rest_framework.exceptions import NotFound
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.side_effect = NotFound("No valid tickers")

        request = self.factory.get('/api/tickers/news/')
        response = self.view(request)
        self.assertEqual(response.status_code, 404)

    @patch('tickers.views.ticker_news.TickerService')
    def test_validation_error_returns_400(self, mock_service_cls):
        from rest_framework.exceptions import ValidationError
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_news_count.side_effect = ValidationError("Invalid count")

        request = self.factory.get('/api/tickers/news/', {'tickers': 'AAPL', 'count': 'bad'})
        response = self.view(request)
        self.assertEqual(response.status_code, 400)


@override_settings(RAW_DEBUG=False)
class TickerNewsViewPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TickerNewsView.as_view()
        self.owner = User.objects.create_user(username='owner', password='pw123456')
        _, self.raw_key = InterviewerKey.create_key(label='test')

    def test_anonymous_no_key_denied(self):
        request = self.factory.get('/api/tickers/news/', {'tickers': 'AAPL'})
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    @patch('tickers.views.ticker_news.TickerService')
    def test_interviewer_key_allowed(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_news_count.return_value = 5
        mock_service.fetch_news.return_value = {'AAPL': [{'title': 'Apple news'}]}

        request = self.factory.get(
            '/api/tickers/news/', {'tickers': 'AAPL'}, HTTP_X_ACCESS_KEY=self.raw_key,
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    @patch('tickers.views.ticker_news.TickerService')
    def test_owner_allowed(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.resolve_tickers.return_value = (['AAPL'], MagicMock())
        mock_service.parse_news_count.return_value = 5
        mock_service.fetch_news.return_value = {'AAPL': [{'title': 'Apple news'}]}

        request = self.factory.get('/api/tickers/news/', {'tickers': 'AAPL'})
        force_authenticate(request, user=self.owner)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
