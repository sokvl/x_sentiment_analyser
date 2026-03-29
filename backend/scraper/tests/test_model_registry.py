from unittest.mock import patch, MagicMock

from django.test import TestCase

from scraper.managers.model_registry import ModelRegistry, MODEL_ID_TO_CONFIG_KEY


MOCK_CONFIGS = {
    'transformer_finbert': {
        'model_name': 'transformer_model',
        'model_lib': 'transformers',
        'params': {'weights_path': 'yiyanghkust/finbert-tone'},
    },
    'transformer_tweetbert': {
        'model_name': 'transformer_model',
        'model_lib': 'transformers',
        'params': {'weights_path': 'cardiffnlp/twitter-roberta-base-sentiment-latest'},
    },
    'cnn_lstm': {
        'model_name': 'lstmcnn_model',
        'model_lib': 'pytorch',
        'params': {
            'weights_path': '/fake/path.pt',
            'vocab_size': 100,
            'embedding_dim': 64,
            'lstm_hidden_dim': 64,
            'num_classes': 3,
            'ticker_vocab_size': 5,
            'dropout': 0.1,
        },
    },
}


class ModelRegistryTests(TestCase):
    def test_available_models_returns_all_ids(self):
        registry = ModelRegistry(MOCK_CONFIGS)
        self.assertEqual(set(registry.available_models), set(MODEL_ID_TO_CONFIG_KEY.keys()))

    def test_loaded_models_initially_empty(self):
        registry = ModelRegistry(MOCK_CONFIGS)
        self.assertEqual(registry.loaded_models, [])

    def test_get_unknown_model_id_raises(self):
        registry = ModelRegistry(MOCK_CONFIGS)
        with self.assertRaises(ValueError) as ctx:
            registry.get('NonExistentModel')
        self.assertIn('NonExistentModel', str(ctx.exception))

    def test_get_unknown_config_key_raises(self):
        # Registry with empty configs
        registry = ModelRegistry({})
        with self.assertRaises(ValueError) as ctx:
            registry.get('FinBERT')
        self.assertIn('transformer_finbert', str(ctx.exception))

    @patch.object(ModelRegistry, '_build_preprocessor')
    @patch('scraper.managers.model_registry.ModelManager')
    def test_get_loads_model_on_first_call(self, mock_mm_cls, mock_build):
        mock_manager = MagicMock()
        mock_mm_cls.return_value = mock_manager
        mock_preprocessor = MagicMock()
        mock_build.return_value = mock_preprocessor

        registry = ModelRegistry(MOCK_CONFIGS)
        manager, preprocessor, model_type = registry.get('FinBERT')

        self.assertEqual(manager, mock_manager)
        self.assertEqual(preprocessor, mock_preprocessor)
        self.assertEqual(model_type, 'transformer_model')
        mock_mm_cls.assert_called_once_with(
            'transformer_model',
            {'weights_path': 'yiyanghkust/finbert-tone'},
        )

    @patch.object(ModelRegistry, '_build_preprocessor')
    @patch('scraper.managers.model_registry.ModelManager')
    def test_get_caches_loaded_model(self, mock_mm_cls, mock_build):
        mock_mm_cls.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        registry = ModelRegistry(MOCK_CONFIGS)
        registry.get('FinBERT')
        registry.get('FinBERT')

        # ModelManager should only be created once
        mock_mm_cls.assert_called_once()

    @patch.object(ModelRegistry, '_build_preprocessor')
    @patch('scraper.managers.model_registry.ModelManager')
    def test_get_different_models_loads_each(self, mock_mm_cls, mock_build):
        mock_mm_cls.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        registry = ModelRegistry(MOCK_CONFIGS)
        registry.get('FinBERT')
        registry.get('TweetBERT')

        self.assertEqual(mock_mm_cls.call_count, 2)
        self.assertIn('FinBERT', registry.loaded_models)
        self.assertIn('TweetBERT', registry.loaded_models)

    @patch.object(ModelRegistry, '_build_preprocessor')
    @patch('scraper.managers.model_registry.ModelManager')
    def test_get_tweetbert_returns_correct_config(self, mock_mm_cls, mock_build):
        mock_mm_cls.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        registry = ModelRegistry(MOCK_CONFIGS)
        _, _, model_type = registry.get('TweetBERT')

        self.assertEqual(model_type, 'transformer_model')
        mock_mm_cls.assert_called_with(
            'transformer_model',
            {'weights_path': 'cardiffnlp/twitter-roberta-base-sentiment-latest'},
        )


class ModelIdToConfigKeyTests(TestCase):
    def test_finbert_maps_correctly(self):
        self.assertEqual(MODEL_ID_TO_CONFIG_KEY['FinBERT'], 'transformer_finbert')

    def test_tweetbert_maps_correctly(self):
        self.assertEqual(MODEL_ID_TO_CONFIG_KEY['TweetBERT'], 'transformer_tweetbert')

    def test_lstmcnn_maps_correctly(self):
        self.assertEqual(MODEL_ID_TO_CONFIG_KEY['LSTMCNNv1'], 'cnn_lstm')
