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
                # Move tokenizer output to target device
                # x_text might be a BatchEncoding (which behaves like a dict) or a Tensor
                if hasattr(x_text, 'items'):
                    # Use a new dict to avoid modifying the input in place if it's a BatchEncoding
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
                predicted_sentiment = torch.argmax(probabilities, dim=-1).cpu()

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


def get_model_predictor(model_name: str) -> BaseModelPredictor:
    predictors = {
        'lstmcnn_model': LSTMCNNPredictor,
        'transformer_model': TransformerModelPredictor,
    }
    if model_name not in predictors:
        raise ValueError(f"Unknown model: {model_name}")
    return predictors[model_name]()
