from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

import torch
import torch.nn as nn


class BaseModelLoader(ABC):
    def __init__(
        self,
        model_params: dict[str, Any] | None = None,
        device: torch.device = None,
    ) -> None:
        self.model_params = model_params if model_params is not None else {}
        self.device = device if device is not None else torch.device('cpu')

    @abstractmethod
    def load_model(
        self,
        model_params: dict[str, Any],
    ) -> nn.Module:
        pass
