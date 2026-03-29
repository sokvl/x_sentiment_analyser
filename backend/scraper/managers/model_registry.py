from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

from django.conf import settings
from transformers import BertTokenizer, AutoTokenizer

from .data_manager.model_processors import get_preprocessor
from .model_manager.model_manager import ModelManager

logger = logging.getLogger(__name__)


MODEL_ID_TO_CONFIG_KEY = {
    'LSTMCNNv1': 'cnn_lstm',
    'FinBERT': 'transformer_finbert',
    'TweetBERT': 'transformer_tweetbert',
}


class ModelRegistry:
    """
    Lazily loads and caches ModelManager + preprocessor pairs.

    Each model is loaded on first request and kept in memory for reuse.
    The registry is safe for concurrent access from multiple threads.
    """

    def __init__(self, model_configs: dict[str, Any]):
        self._configs = model_configs
        self._managers: dict[str, ModelManager] = {}
        self._preprocessors: dict[str, Any] = {}
        self._lock = Lock()

    def _load_json(self, path: str) -> dict:
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    def _build_preprocessor(self, model_name: str, model_params: dict) -> Any:
        if model_name == 'lstmcnn_model':
            word_to_index = self._load_json(settings.WORD_TO_INDEX_PATH)
            return get_preprocessor(
                model_name,
                word_to_index=word_to_index,
                max_len=30,
                pad_token=0,
            )

        # All transformer variants use AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_params['weights_path'])
        return get_preprocessor('transformer_model', tokenizer=tokenizer)

    def _ensure_loaded(self, config_key: str) -> None:
        """Load a model into the registry if not already present."""
        if config_key in self._managers:
            return

        with self._lock:
            if config_key in self._managers:
                return

            if config_key not in self._configs:
                raise ValueError(
                    f"Unknown model config key '{config_key}'. "
                    f"Available: {list(self._configs.keys())}"
                )

            cfg = self._configs[config_key]
            model_name = cfg['model_name']
            model_params = cfg['params']

            logger.info('Loading model %s (%s) ...', config_key, model_name)
            manager = ModelManager(model_name, model_params)
            preprocessor = self._build_preprocessor(model_name, model_params)

            self._managers[config_key] = manager
            self._preprocessors[config_key] = preprocessor
            logger.info('Model %s loaded successfully.', config_key)

    def get(self, model_id: str) -> tuple[ModelManager, Any, str]:
        """
        Returns (model_manager, preprocessor, model_type) for a user-facing
        model ID such as 'FinBERT' or 'TweetBERT'.

        Raises ValueError if the model ID is unknown.
        """
        config_key = MODEL_ID_TO_CONFIG_KEY.get(model_id)
        if config_key is None:
            raise ValueError(
                f"Unknown model ID '{model_id}'. "
                f"Available: {list(MODEL_ID_TO_CONFIG_KEY.keys())}"
            )

        self._ensure_loaded(config_key)
        manager = self._managers[config_key]
        preprocessor = self._preprocessors[config_key]
        model_type = self._configs[config_key]['model_name']
        return manager, preprocessor, model_type

    @property
    def available_models(self) -> list[str]:
        return list(MODEL_ID_TO_CONFIG_KEY.keys())

    @property
    def loaded_models(self) -> list[str]:
        return [
            model_id for model_id, key in MODEL_ID_TO_CONFIG_KEY.items()
            if key in self._managers
        ]
