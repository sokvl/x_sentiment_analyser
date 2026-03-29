from datetime import datetime

from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from tickers.models import Ticker
from scraper.models import Config, Source, Content, PostMeta, PostPrediction, Post


class ConfigModelTests(TestCase):
    def test_create_config(self):
        config = Config.objects.create(
            name='test_config',
            active=True,
            config_string={'user_config': {'key': 'value'}, 'scrapers_config': []},
        )
        self.assertEqual(config.name, 'test_config')
        self.assertTrue(config.active)
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)

    def test_config_string_is_json(self):
        config = Config.objects.create(
            name='json_test', active=False,
            config_string={'nested': {'data': [1, 2, 3]}},
        )
        config.refresh_from_db()
        self.assertEqual(config.config_string['nested']['data'], [1, 2, 3])


class SourceModelTests(TestCase):
    def test_create_source(self):
        source = Source.objects.create(
            name='Twitter', base_url='https://x.com',
            login_required=True, category='social',
        )
        self.assertEqual(source.name, 'Twitter')
        self.assertEqual(str(source), 'Twitter')

    def test_unique_name(self):
        Source.objects.create(name='Twitter', category='social')
        with self.assertRaises(IntegrityError):
            Source.objects.create(name='Twitter', category='social2')

    def test_credentials_id_nullable(self):
        source = Source.objects.create(name='RSS', category='news')
        self.assertIsNone(source.credentials_id)


class ContentModelTests(TestCase):
    def test_create_content(self):
        content = Content.objects.create(text='$AAPL is going to the moon!')
        self.assertEqual(content.text, '$AAPL is going to the moon!')
        self.assertIsNotNone(content.created_at)


class PostMetaModelTests(TestCase):
    def test_create_with_all_fields(self):
        source = Source.objects.create(name='Twitter', category='social')
        meta = PostMeta.objects.create(
            source=source, likes=100, views=5000, shares=20, comments=10,
        )
        self.assertEqual(meta.likes, 100)

    def test_nullable_fields(self):
        meta = PostMeta.objects.create()
        self.assertIsNone(meta.likes)
        self.assertIsNone(meta.views)
        self.assertIsNone(meta.shares)
        self.assertIsNone(meta.comments)
        self.assertIsNone(meta.source)


class PostPredictionModelTests(TestCase):
    def test_create_prediction(self):
        pred = PostPrediction.objects.create(
            prediction=2,
            probabilities=[0.1, 0.2, 0.7],
            model_name='LSTMCNNv1',
        )
        self.assertEqual(pred.prediction, 2)
        self.assertEqual(pred.probabilities, [0.1, 0.2, 0.7])
        self.assertIsNotNone(pred.created_at)


class PostModelTests(TestCase):
    def setUp(self):
        self.ticker = Ticker.objects.create(
            symbol='AAPL', type='stock', full_name='Apple Inc.'
        )
        self.content = Content.objects.create(text='Test tweet about $AAPL')
        self.meta = PostMeta.objects.create(likes=10)
        self.prediction = PostPrediction.objects.create(
            prediction=1, probabilities=[0.3, 0.4, 0.3], model_name='test',
        )

    def test_create_post(self):
        post = Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=self.ticker,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )
        self.assertIsNotNone(post.post_id)
        self.assertEqual(post.related_ticker, self.ticker)

    def test_default_ordering_by_timestamp_desc(self):
        now = timezone.now()
        Post.objects.create(
            time_stamp=now - timezone.timedelta(hours=2),
            related_ticker=self.ticker,
            related_content=Content.objects.create(text='older'),
            post_metadata=PostMeta.objects.create(),
            post_prediction=PostPrediction.objects.create(
                prediction=0, probabilities=[0.8, 0.1, 0.1], model_name='t',
            ),
        )
        Post.objects.create(
            time_stamp=now,
            related_ticker=self.ticker,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )
        posts = list(Post.objects.all())
        self.assertGreater(posts[0].time_stamp, posts[1].time_stamp)

    def test_ticker_nullable(self):
        post = Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=None,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )
        self.assertIsNone(post.related_ticker)

    def test_cascade_delete_content(self):
        Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=self.ticker,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )
        self.content.delete()
        self.assertEqual(Post.objects.count(), 0)

    def test_ticker_set_null_on_delete(self):
        post = Post.objects.create(
            time_stamp=timezone.now(),
            related_ticker=self.ticker,
            related_content=self.content,
            post_metadata=self.meta,
            post_prediction=self.prediction,
        )
        self.ticker.delete()
        post.refresh_from_db()
        self.assertIsNone(post.related_ticker)
