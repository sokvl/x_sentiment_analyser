from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from tickers.models import Ticker
from tickers.views.ticker import TickerViewSet
from tickers.views.stock_data import StockDataView


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
