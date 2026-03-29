from unittest.mock import MagicMock

from django.test import TestCase

from scraper.managers.data_manager.model_processors import (
    LSTMCNNPreprocessor,
    TransformerPreprocessor,
    get_preprocessor,
)


class LSTMCNNPreprocessorTests(TestCase):
    def setUp(self):
        self.word_to_index = {
            'apple': 1, 'stock': 2, 'is': 3, 'going': 4, 'up': 5,
            'the': 6, 'market': 7, 'bullish': 8,
        }
        self.preprocessor = LSTMCNNPreprocessor(
            word_to_index=self.word_to_index,
            max_len=10,
            pad_token=0,
        )

    def test_basic_preprocessing(self):
        result = self.preprocessor.preprocess('Apple stock is going up')
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 1)  # apple
        self.assertEqual(result[1], 2)  # stock
        self.assertEqual(result[2], 3)  # is
        self.assertEqual(result[3], 4)  # going
        self.assertEqual(result[4], 5)  # up

    def test_pads_short_text(self):
        result = self.preprocessor.preprocess('apple')
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1:], [0] * 9)

    def test_truncates_long_text(self):
        long_text = ' '.join(['apple'] * 20)
        result = self.preprocessor.preprocess(long_text)
        self.assertEqual(len(result), 10)

    def test_removes_urls(self):
        result = self.preprocessor.preprocess('apple https://example.com stock')
        self.assertNotEqual(result[0], 0)  # 'apple' should map to something

    def test_removes_hashtags(self):
        result = self.preprocessor.preprocess('#trending apple stock')
        # '#trending' should be removed, 'apple stock' should remain
        self.assertEqual(result[0], 1)  # apple
        self.assertEqual(result[1], 2)  # stock

    def test_removes_special_characters(self):
        result = self.preprocessor.preprocess('apple!!! stock??? $$$')
        self.assertEqual(result[0], 1)  # apple
        self.assertEqual(result[1], 2)  # stock

    def test_lowercases_text(self):
        result = self.preprocessor.preprocess('APPLE STOCK')
        self.assertEqual(result[0], 1)  # 'apple' after lowering
        self.assertEqual(result[1], 2)  # 'stock'

    def test_unknown_words_get_pad_token(self):
        result = self.preprocessor.preprocess('xyzxyz')
        self.assertEqual(result[0], 0)

    def test_empty_text(self):
        result = self.preprocessor.preprocess('')
        self.assertEqual(result, [0] * 10)


class TransformerPreprocessorTests(TestCase):
    def test_calls_tokenizer(self):
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {'input_ids': [101, 2003, 102]}
        preprocessor = TransformerPreprocessor(mock_tokenizer)

        result = preprocessor.preprocess('test text')
        mock_tokenizer.assert_called_once_with(
            'test text',
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=512,
        )


class GetPreprocessorTests(TestCase):
    def test_returns_lstm_preprocessor(self):
        preprocessor = get_preprocessor(
            'lstmcnn_model',
            word_to_index={'a': 1},
            max_len=10,
            pad_token=0,
        )
        self.assertIsInstance(preprocessor, LSTMCNNPreprocessor)

    def test_returns_transformer_preprocessor(self):
        preprocessor = get_preprocessor(
            'transformer_model',
            tokenizer=MagicMock(),
        )
        self.assertIsInstance(preprocessor, TransformerPreprocessor)

    def test_unknown_preprocessor_raises(self):
        with self.assertRaises(ValueError):
            get_preprocessor('unknown_model')
