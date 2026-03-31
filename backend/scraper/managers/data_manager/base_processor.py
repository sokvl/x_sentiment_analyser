from __future__ import annotations

import re
from abc import ABC, abstractmethod


class BasePreprocessor(ABC):
    """Template Method preprocessor.

    Subclasses define a ``pipeline`` — an ordered list of cleaning step names.
    Each step is a method on this base class (shared) or on the subclass
    (model-specific).  Only steps listed in the pipeline are executed.

    The final ``tokenize`` step converts cleaned text into model input and
    must be implemented by every subclass.
    """

    # Subclasses override this to declare which cleaning steps to run,
    # in order, before tokenization.
    pipeline: list[str] = []

    def preprocess(self, text: str, **kwargs):
        """Run the full pipeline: clean → tokenize."""
        cleaned = self.clean(text)
        return self.tokenize(cleaned, **kwargs)

    def clean(self, text: str) -> str:
        """Execute every step listed in ``self.pipeline`` sequentially."""
        for step_name in self.pipeline:
            method = getattr(self, step_name, None)
            if method is None:
                raise AttributeError(
                    f"{type(self).__name__} pipeline references "
                    f"'{step_name}' but no such method exists."
                )
            text = method(text)
        return text

    @abstractmethod
    def tokenize(self, text: str, **kwargs):
        """Convert cleaned text into model-specific input."""

    # ------------------------------------------------------------------
    # Shared cleaning steps — available to any subclass that lists them
    # ------------------------------------------------------------------

    @staticmethod
    def lowercase(text: str) -> str:
        return text.lower()

    @staticmethod
    def strip_urls(text: str) -> str:
        return re.sub(r'http\S+', '', text)

    @staticmethod
    def strip_mentions(text: str) -> str:
        return re.sub(r'@\w+', '', text)

    @staticmethod
    def strip_hashtags(text: str) -> str:
        return re.sub(r'#\w+', '', text)

    @staticmethod
    def strip_special_chars(text: str) -> str:
        """Remove everything except letters and whitespace."""
        return re.sub(r'[^a-zA-Z\s]', '', text)

    @staticmethod
    def strip_numbers(text: str) -> str:
        return re.sub(r'\d+', '', text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r'\s{2,}', ' ', text).strip()
