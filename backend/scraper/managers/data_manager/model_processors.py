from __future__ import annotations

import re

from .base_processor import BasePreprocessor


class LSTMCNNPreprocessor(BasePreprocessor):
    def __init__(self, word_to_index: dict, max_len: int, pad_token: int = 0):
        self.word_to_index = word_to_index
        self.max_len = max_len
        self.pad_token = pad_token

    def _clean_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def preprocess(self, text: str, **kwargs):
        cleaned_text = self._clean_text(text)
        tokens = cleaned_text.split()
        token_indices = [
            self.word_to_index.get(
                word, self.pad_token,
            ) for word in tokens
        ]
        if len(token_indices) < self.max_len:
            token_indices += [self.pad_token] * \
                (self.max_len - len(token_indices))
        else:
            token_indices = token_indices[:self.max_len]
        return token_indices


class TransformerPreprocessor(BasePreprocessor):
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def preprocess(self, text: str, **kwargs):
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
