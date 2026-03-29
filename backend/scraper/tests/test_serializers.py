from django.test import TestCase
from django.utils import timezone

from scraper.models import Config, Source, Content, PostMeta, PostPrediction, Post
from scraper.serializers import (
    ConfigSerializer, PostSerializer, PostMetaSerializer,
    PostPredictionSerializer, EvalRequestSerializer, EvalResponseSerializer,
    SourceSerializer,
)
from tickers.models import Ticker


class ConfigSerializerTests(TestCase):
    def test_valid_config_string(self):
        data = {
            'name': 'test',
            'active': True,
            'config_string': {
                'user_config': {'key': 'value'},
                'scrapers_config': [{'name': 'twitter'}],
            },
        }
        serializer = ConfigSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_user_config_invalid(self):
        data = {
            'name': 'test',
            'active': True,
            'config_string': {'scrapers_config': []},
        }
        serializer = ConfigSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_missing_scrapers_config_invalid(self):
        data = {
            'name': 'test',
            'active': True,
            'config_string': {'user_config': {}},
        }
        serializer = ConfigSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_user_config_must_be_dict(self):
        data = {
            'name': 'test',
            'active': True,
            'config_string': {'user_config': 'not a dict', 'scrapers_config': []},
        }
        serializer = ConfigSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_scrapers_config_must_be_list(self):
        data = {
            'name': 'test',
            'active': True,
            'config_string': {'user_config': {}, 'scrapers_config': 'not a list'},
        }
        serializer = ConfigSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class SourceSerializerTests(TestCase):
    def test_serializes_source(self):
        source = Source.objects.create(
            name='Twitter', base_url='https://x.com',
            login_required=True, category='social',
        )
        serializer = SourceSerializer(source)
        data = serializer.data
        self.assertEqual(data['name'], 'Twitter')
        self.assertEqual(data['category'], 'social')

    def test_valid_deserialization(self):
        data = {'name': 'Reddit', 'base_url': 'https://reddit.com', 'category': 'forum'}
        serializer = SourceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class EvalRequestSerializerTests(TestCase):
    def test_valid_request(self):
        data = {
            'tweet': 'AAPL is mooning!',
            'ticker': '$AAPL',
            'source_name': 'test',
            'date': '2024-01-15',
        }
        serializer = EvalRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_tweet_invalid(self):
        data = {'ticker': '$AAPL', 'source_name': 'test', 'date': '2024-01-15'}
        serializer = EvalRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_missing_ticker_invalid(self):
        data = {'tweet': 'test', 'source_name': 'test', 'date': '2024-01-15'}
        serializer = EvalRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class EvalResponseSerializerTests(TestCase):
    def test_serializes_response(self):
        data = {
            'text': 'test tweet',
            'ticker': '$AAPL',
            'processed_text': [1, 2, 3, 0, 0],
            'prediction': 2,
            'predicted_probabilities': [0.1, 0.2, 0.7],
        }
        serializer = EvalResponseSerializer(data)
        output = serializer.data
        self.assertEqual(output['text'], 'test tweet')
        self.assertEqual(output['predicted_sentiment'], 2)
        self.assertEqual(output['predicted_probabilities'], [0.1, 0.2, 0.7])


class PostSerializerTests(TestCase):
    def test_serializes_post_with_nested_relations(self):
        ticker = Ticker.objects.create(symbol='AAPL', type='stock', full_name='Apple Inc.')
        content = Content.objects.create(text='Test')
        source = Source.objects.create(name='Test', category='test')
        meta = PostMeta.objects.create(source=source, likes=10)
        prediction = PostPrediction.objects.create(
            prediction=1, probabilities=[0.3, 0.4, 0.3], model_name='test',
        )
        post = Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=ticker,
            related_content=content,
            post_metadata=meta,
            post_prediction=prediction,
        )
        serializer = PostSerializer(post)
        data = serializer.data
        self.assertEqual(data['related_ticker']['symbol'], 'AAPL')
        self.assertEqual(data['related_content']['text'], 'Test')
        self.assertEqual(data['post_metadata']['likes'], 10)
        self.assertEqual(data['post_prediction']['prediction'], 1)
