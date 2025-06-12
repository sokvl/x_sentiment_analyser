from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from django.conf import settings

from .model_loaders import get_model_loader
from .model_predictors import get_model_predictor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class ModelManager:
    def __init__(
        self,
        model_name: str,
        model_params: dict[str, Any] | None = None,
        device: torch.device | None = None,
    ) -> None:
        self.model_name = model_name
        self.model_params = model_params if model_params is not None else {}
        self.device = device or torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu',
        )
        self.model: nn.Module | None = None
        self.loader = get_model_loader(
            self.model_name, self.model_params, self.device,
        )
        self.predictor = get_model_predictor(self.model_name)
        self.load_model()

    def load_model(self, model_params: dict[str, Any] | None = None):
        """Load weights and instantiate the model.

        If *model_params* is omitted we fall back to the ones supplied during construction.
        """
        if model_params is None:
            model_params = self.model_params

        self.model = self.loader.load_model(
            model_params,
        )
        return self

    def save_model(self, save_path: str | Path | None = None) -> None:
        if self.model is None:
            logger.error('Model is not initialized. Cannot save.')
            raise ValueError('Model is not initialized. Cannot save.')
        if save_path is None:
            save_path = settings.MODEL_WEIGHTS_PATH

        save_path = Path(save_path)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {'model_state_dict': self.model.state_dict()}, save_path,
            )
            logger.info(f"Weights saved in: {save_path}.")
        except Exception as e:
            logger.error(f"Can't save model: {e}")
            raise

    def predict(
        self,
        x_text: list[int] | torch.Tensor,
        x_ticker: list[int] | torch.Tensor,
    ) -> dict[str, int | list[float]]:
        if self.model is None:
            logger.error(
                'Model is not initialized. Please call `load_model` first.',
            )
            raise ValueError(
                'Model is not initialized. Please call `load_model` first.',
            )

        return self.predictor.predict(self.model, x_text, x_ticker, self.device)

    def get_model(self) -> nn.Module:
        if self.model is None:
            raise ValueError(
                'Model is not loaded. Please call `load_model` first.',
            )
        return self.model

    def get_device(self) -> torch.device:
        if self.model is None:
            logger.error(
                'Device not available because model is not initialized.',
            )
            raise ValueError(
                'Device not available because model is not initialized.',
            )
        return self.device

    def set_device(self, device: torch.device) -> None:
        if self.model is None:
            logger.error('Model is not initialized. Cannot change device.')
            raise ValueError('Model is not initialized. Cannot change device.')

        if not isinstance(device, torch.device):
            logger.error(
                'Invalid device provided. Must be a torch.device instance.',
            )
            raise ValueError(
                'Invalid device provided. Must be a torch.device instance.',
            )

        try:
            self.device = device
            self.model.to(self.device)
            logger.info(f"Model moved to: {self.device}")
        except Exception as e:
            logger.error(f"Moving model to {device} failed: {e}")
            raise

    @staticmethod
    def load_params(path: str | Path) -> dict[str, Any]:
        path = Path(path)
        try:
            with path.open('r', encoding='utf-8') as file:
                params = json.load(file)
            logger.info(f"Parameters loaded from {path}")
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            raise ValueError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in file {path}: {e}")
            raise ValueError(f"JSON decode error in {path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading parameters: {e}")
            raise ValueError(
                f"Unexpected error loading parameters from {path}: {e}",
            )

        logger.info('Parameters successfully verified.')
        return params

    def get_modelname(self):
        return self.model_name
