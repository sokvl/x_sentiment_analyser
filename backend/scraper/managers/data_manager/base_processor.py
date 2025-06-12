from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class BasePreprocessor(ABC):
    @abstractmethod
    def preprocess(self, text: str, **kwargs):
        pass
