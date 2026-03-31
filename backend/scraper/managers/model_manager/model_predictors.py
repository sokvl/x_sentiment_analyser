from __future__ import annotations

import logging

import torch
import torch.nn as nn

from .base_predictor import BaseModelPredictor

logger = logging.getLogger(__name__)


class LSTMCNNPredictor(BaseModelPredictor):
    def predict(
        self,
        model: nn.Module,
        x_text: list[int] | torch.Tensor,
        x_ticker: list[int] | torch.Tensor,
        device: torch.device,
    ) -> dict[str, int | list[float]]:
        model.eval()
        try:
            with torch.no_grad():
                x_text_tensor = torch.tensor(
                    x_text, dtype=torch.long,
                ).to(device)
                x_ticker_tensor = torch.tensor(
                    x_ticker, dtype=torch.long,
                ).to(device)

                if x_text_tensor.dim() == 1:
                    x_text_tensor = x_text_tensor.unsqueeze(0)

                output = model(x_text_tensor, x_ticker_tensor)
                probabilities = torch.nn.functional.softmax(
                    output, dim=1,
                ).cpu()
                predicted_sentiment = torch.argmax(probabilities, dim=1).cpu()

            return {
                'predicted_sentiment': int(predicted_sentiment.item()),
                'predicted_probabilities': probabilities.squeeze(0).tolist()
                if probabilities.size(0) == 1 else probabilities.tolist(),
            }
        except Exception as e:
            logger.exception('Prediction failed for LSTMCNN model')
            raise RuntimeError(f"Prediction failed for LSTMCNN: {e}") from e


class TransformerModelPredictor(BaseModelPredictor):
    """Predictor for HuggingFace transformer models.

    Supports an optional ``label_map`` that remaps model-native label indices
    to the project-standard ordering (0=negative, 1=neutral, 2=positive).

    For example FinBERT (yiyanghkust/finbert-tone) outputs:
        LABEL_0 = neutral, LABEL_1 = positive, LABEL_2 = negative
    The label_map ``[1, 2, 0]`` translates this to standard ordering.
    """

    def __init__(self, label_map: list[int] | None = None):
        self.label_map = label_map

    def _remap(
        self, probabilities: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Reorder probability columns according to ``label_map`` and
        return (remapped_probs, predicted_class)."""
        if self.label_map is None:
            predicted = torch.argmax(probabilities, dim=-1)
            return probabilities, predicted

        # Build a new tensor with columns in standard order.
        num_classes = probabilities.size(-1)
        remapped = torch.zeros_like(probabilities)
        for model_idx, standard_idx in enumerate(self.label_map):
            if standard_idx < num_classes:
                remapped[..., standard_idx] = probabilities[..., model_idx]

        predicted = torch.argmax(remapped, dim=-1)
        return remapped, predicted

    def predict(
        self,
        model: nn.Module,
        x_text: list[int] | torch.Tensor,
        x_ticker: list[int] | torch.Tensor,
        device: torch.device,
    ) -> dict[str, int | list[float]]:
        model.eval()
        try:
            with torch.no_grad():
                if hasattr(x_text, 'items'):
                    x_text_moved = {}
                    for k, v in x_text.items():
                        if isinstance(v, torch.Tensor):
                            x_text_moved[k] = v.to(device)
                        else:
                            x_text_moved[k] = v
                    x_text = x_text_moved
                elif isinstance(x_text, torch.Tensor):
                    x_text = x_text.to(device)
                elif isinstance(x_text, list):
                    x_text = torch.tensor(x_text, dtype=torch.long).to(device)

                if isinstance(x_text, dict):
                    output = model(**x_text)
                else:
                    output = model(x_text)

                logits = output.logits if hasattr(output, 'logits') else output[0]
                probabilities = torch.nn.functional.softmax(
                    logits, dim=1,
                ).cpu()

                probabilities, predicted_sentiment = self._remap(probabilities)

            return {
                'predicted_sentiment': int(predicted_sentiment.item()),
                'predicted_probabilities': probabilities.squeeze(0).tolist()
                if probabilities.size(0) == 1 else probabilities.tolist(),
            }
        except Exception as e:
            logger.exception('Error during transformer model prediction')
            raise RuntimeError(
                f"Prediction failed for transformer model: {e}",
            ) from e


def get_model_predictor(
    model_name: str,
    label_map: list[int] | None = None,
) -> BaseModelPredictor:
    if model_name == 'lstmcnn_model':
        return LSTMCNNPredictor()
    if model_name == 'transformer_model':
        return TransformerModelPredictor(label_map=label_map)
    raise ValueError(f"Unknown model: {model_name}")
