from __future__ import annotations

from abc import ABC
from abc import abstractmethod

import torch
import torch.nn as nn


class BaseModelPredictor(ABC):
    @abstractmethod
    def predict(
        self,
        model: nn.Module,
        x_text: list[int] | torch.Tensor,
        x_ticker: list[int] | torch.Tensor,
        device: torch.device,
    ) -> dict[str, int | list[float]]:
        pass
