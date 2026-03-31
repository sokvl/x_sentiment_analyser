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

    # --- Pipeline step tests ---

    def test_pipeline_has_expected_steps(self):
        self.assertEqual(self.preprocessor.pipeline, [
            'lowercase', 'strip_urls', 'strip_hashtags',
            'strip_special_chars', 'normalize_whitespace',
        ])

    def test_clean_lowercases(self):
        self.assertIn('apple', self.preprocessor.clean('APPLE'))

    def test_clean_strips_urls(self):
        cleaned = self.preprocessor.clean('apple https://example.com stock')
        self.assertNotIn('http', cleaned)

    def test_clean_strips_hashtags(self):
        cleaned = self.preprocessor.clean('#trending apple')
        self.assertNotIn('#trending', cleaned)
        self.assertIn('apple', cleaned)

    def test_clean_strips_special_chars(self):
        cleaned = self.preprocessor.clean('apple!!! stock???')
        self.assertEqual(cleaned, 'apple stock')

    # --- Full preprocess tests ---

    def test_basic_preprocessing(self):
        result = self.preprocessor.preprocess('Apple stock is going up')
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 1)   # apple
        self.assertEqual(result[1], 2)   # stock
        self.assertEqual(result[2], 3)   # is
        self.assertEqual(result[3], 4)   # going
        self.assertEqual(result[4], 5)   # up

    def test_pads_short_text(self):
        result = self.preprocessor.preprocess('apple')
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1:], [0] * 9)

    def test_truncates_long_text(self):
        long_text = ' '.join(['apple'] * 20)
        result = self.preprocessor.preprocess(long_text)
        self.assertEqual(len(result), 10)

    def test_unknown_words_get_pad_token(self):
        result = self.preprocessor.preprocess('xyzxyz')
        self.assertEqual(result[0], 0)

    def test_empty_text(self):
        result = self.preprocessor.preprocess('')
        self.assertEqual(result, [0] * 10)


class TransformerPreprocessorTests(TestCase):
    def setUp(self):
        self.mock_tokenizer = MagicMock()
        self.mock_tokenizer.return_value = {'input_ids': [101, 2003, 102]}
        self.preprocessor = TransformerPreprocessor(self.mock_tokenizer)

    def test_pipeline_has_expected_steps(self):
        self.assertEqual(self.preprocessor.pipeline, [
            'strip_urls', 'strip_mentions', 'normalize_whitespace',
        ])

    def test_clean_strips_urls(self):
        cleaned = self.preprocessor.clean('check https://t.co/abc this')
        self.assertNotIn('http', cleaned)

    def test_clean_strips_mentions(self):
        cleaned = self.preprocessor.clean('@elonmusk is bullish')
        self.assertNotIn('@elonmusk', cleaned)
        self.assertIn('bullish', cleaned)

    def test_clean_preserves_case(self):
        cleaned = self.preprocessor.clean('TSLA is Bullish')
        self.assertIn('TSLA', cleaned)
        self.assertIn('Bullish', cleaned)

    def test_clean_preserves_hashtags(self):
        cleaned = self.preprocessor.clean('#TSLA moon')
        self.assertIn('#TSLA', cleaned)

    def test_calls_tokenizer_with_cleaned_text(self):
        self.preprocessor.preprocess('check https://t.co/x @user text')
        self.mock_tokenizer.assert_called_once_with(
            'check text',
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
