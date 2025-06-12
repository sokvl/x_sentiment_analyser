# Add imports
from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

import torch
import torch.nn as nn
from transformers import AutoModelForSequenceClassification

from .base_loader import BaseModelLoader


class LSTMCNNLoader(BaseModelLoader):
    def load_model(self, model_params: dict[str, Any]) -> nn.Module:
        """Initialise CNN-LSTM architecture and load weights."""
        from models.lstm_cnn import CNNLSTMModel  # snake_case import

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

        weights_path = Path(model_params['weights_path'])
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
        """Load a HuggingFace transformer model for sequence classification."""
        try:
            model = AutoModelForSequenceClassification.from_pretrained(
                model_params['weights_path'],
            )
            model.to(self.device)
        except Exception as e:
            raise RuntimeError(f"Error loading Transformer model: {e}") from e
        return model


def get_model_loader(model_name: str | None, model_params: dict[str, Any] | None, device: torch.device) -> BaseModelLoader:
    loaders = {
        'lstmcnn_model': LSTMCNNLoader,
        'transformer_model': TransformerModelLoader,
    }
    if model_name not in loaders:
        raise ValueError(f"Unknown model: {model_name}")
    return loaders[model_name](
        model_params,
        device,
    )
