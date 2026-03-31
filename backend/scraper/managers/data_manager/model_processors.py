from __future__ import annotations

from .base_processor import BasePreprocessor


class LSTMCNNPreprocessor(BasePreprocessor):
    """Aggressive cleaning for a bag-of-words style model.

    Pipeline: lowercase → URLs → hashtags → special chars → whitespace
    Then tokenize to padded integer indices.
    """

    pipeline = [
        'lowercase',
        'strip_urls',
        'strip_hashtags',
        'strip_special_chars',
        'normalize_whitespace',
    ]

    def __init__(self, word_to_index: dict, max_len: int, pad_token: int = 0):
        self.word_to_index = word_to_index
        self.max_len = max_len
        self.pad_token = pad_token

    def tokenize(self, text: str, **kwargs):
        tokens = text.split()
        indices = [self.word_to_index.get(w, self.pad_token) for w in tokens]

        if len(indices) < self.max_len:
            indices += [self.pad_token] * (self.max_len - len(indices))
        else:
            indices = indices[: self.max_len]
        return indices


class TransformerPreprocessor(BasePreprocessor):
    """Light cleaning for BERT-family models.

    Pipeline: URLs → mentions → whitespace
    Stopwords are NOT removed — transformer attention relies on them.
    No lowercasing — BERT's WordPiece vocabulary is case-aware.
    """

    pipeline = [
        'strip_urls',
        'strip_mentions',
        'normalize_whitespace',
    ]

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def tokenize(self, text: str, **kwargs):
        return self.tokenizer(
            text,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=512,
        )


def get_preprocessor(name: str, **kwargs):
    preprocessors = {
        'lstmcnn_model': LSTMCNNPreprocessor,
        'transformer_model': TransformerPreprocessor,
    }
    if name not in preprocessors:
        raise ValueError(f"Preprocessor '{name}' is not recognized.")
    return preprocessors[name](**kwargs)
