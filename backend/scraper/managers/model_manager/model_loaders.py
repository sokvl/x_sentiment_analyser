from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from transformers import (
    AutoModelForSequenceClassification,
    BertForSequenceClassification,
)

from .base_loader import BaseModelLoader

# HuggingFace model IDs that require the explicit Bert* classes.
_BERT_MODEL_HF_IDS = {
    'yiyanghkust/finbert-tone',
    'nickmuchi/finbert-tone-finetuned-fintwitter-classification',
}


class LSTMCNNLoader(BaseModelLoader):
    def load_model(self, model_params: dict[str, Any]) -> nn.Module:
        """Initialise CNN-LSTM architecture and load weights."""
        from ml_logic.lstm_cnn import CNNLSTMModel

        try:
            model = CNNLSTMModel(
                vocab_size=model_params['vocab_size'],
                embedding_dim=model_params['embedding_dim'],
                lstm_hidden_dim=model_params['lstm_hidden_dim'],
                num_classes=model_params['num_classes'],
                ticker_vocab_size=model_params['ticker_vocab_size'],
                dropout=model_params['dropout'],
            ).to(self.device)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialise CNN_LSTM_Model: {e}",
            ) from e

        weights_path = Path(model_params['resolved_weights'])
        try:
            checkpoint = torch.load(weights_path, map_location=self.device)
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            model.load_state_dict(state_dict)
        except FileNotFoundError:
            raise FileNotFoundError(f"Weight file not found: {weights_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading LSTM/CNN weights: {e}") from e

        return model


class TransformerModelLoader(BaseModelLoader):
    def load_model(self, model_params: dict[str, Any]) -> nn.Module:
        """Load a HuggingFace transformer model for sequence classification.

        Uses ``BertForSequenceClassification`` for known FinBERT variants and
        ``AutoModelForSequenceClassification`` for everything else.
        The model identifier comes from ``resolved_weights`` (set during config
        validation — either a local path or a HuggingFace hub ID).
        """
        resolved = model_params['resolved_weights']
        num_labels = model_params.get('num_labels', 3)

        try:
            if resolved in _BERT_MODEL_HF_IDS:
                model = BertForSequenceClassification.from_pretrained(
                    resolved, num_labels=num_labels,
                )
            else:
                model = AutoModelForSequenceClassification.from_pretrained(
                    resolved, num_labels=num_labels,
                )
            model.to(self.device)
        except Exception as e:
            raise RuntimeError(f"Error loading Transformer model: {e}") from e
        return model


def get_model_loader(
    model_name: str | None,
    model_params: dict[str, Any] | None,
    device: torch.device,
) -> BaseModelLoader:
    loaders = {
        'lstmcnn_model': LSTMCNNLoader,
        'transformer_model': TransformerModelLoader,
    }
    if model_name not in loaders:
        raise ValueError(f"Unknown model: {model_name}")
    return loaders[model_name](model_params, device)
