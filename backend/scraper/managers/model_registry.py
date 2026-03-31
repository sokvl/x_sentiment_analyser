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

# HuggingFace model IDs that use BertTokenizer instead of AutoTokenizer.
_BERT_TOKENIZER_HF_IDS = {
    'yiyanghkust/finbert-tone',
    'nickmuchi/finbert-tone-finetuned-fintwitter-classification',
}


class ModelConfigError(Exception):
    """Raised when model configuration is invalid and unrecoverable."""


class ModelRegistry:
    """
    Lazily loads and caches ModelManager + preprocessor pairs.

    At construction time every config entry is validated:
      - Local ``weights_path`` is checked for existence.
      - If invalid / missing, the registry falls back to ``hf_fallback``.
      - If *both* are absent the model is marked unavailable and an error is
        logged (but doesn't crash the process so other models can still work).

    Each model is loaded on first request and kept in memory for reuse.
    The registry is safe for concurrent access from multiple threads.
    """

    def __init__(self, model_configs: dict[str, Any]):
        self._configs = model_configs
        self._managers: dict[str, ModelManager] = {}
        self._preprocessors: dict[str, Any] = {}
        self._lock = Lock()
        self._unavailable: set[str] = set()

        self._validate_and_resolve_configs()

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def _validate_and_resolve_configs(self) -> None:
        """Check every model config entry at startup.

        For each entry the ``resolved_weights`` param is set to the actual
        path/identifier the loaders should use at load time.

        Rules:
        1. If ``weights_path`` points to an existing local file → use it.
        2. Otherwise fall back to ``hf_fallback`` (HuggingFace hub ID).
        3. If neither is usable → mark config as *unavailable*.
        """
        for config_key, cfg in self._configs.items():
            params = cfg.get('params', {})
            model_name = cfg.get('model_name', '')
            local_path = params.get('weights_path')
            hf_fallback = params.get('hf_fallback')

            # --- Resolve effective weights source ---
            if local_path and Path(local_path).exists():
                params['resolved_weights'] = local_path
                logger.info(
                    '[%s] Using local weights: %s', config_key, local_path,
                )
            elif hf_fallback:
                if local_path:
                    logger.warning(
                        '[%s] Local weights_path "%s" not found — '
                        'falling back to HuggingFace: %s',
                        config_key, local_path, hf_fallback,
                    )
                else:
                    logger.info(
                        '[%s] No local weights_path specified — '
                        'using HuggingFace: %s',
                        config_key, hf_fallback,
                    )
                params['resolved_weights'] = hf_fallback
            else:
                # Nothing usable at all.
                logger.error(
                    '[%s] No valid weights_path and no hf_fallback configured. '
                    'Model will be UNAVAILABLE.',
                    config_key,
                )
                self._unavailable.add(config_key)
                continue

            # --- Extra checks per model type ---
            if model_name == 'lstmcnn_model':
                self._validate_lstm_extras(config_key, params)

        if self._unavailable:
            logger.warning(
                'The following model configs are unavailable and will raise '
                'on access: %s', sorted(self._unavailable),
            )

    def _validate_lstm_extras(self, config_key: str, params: dict) -> None:
        """LSTM models need supporting files (word_to_index, ticker_to_index)."""
        for label, path in [
            ('WORD_TO_INDEX_PATH', settings.WORD_TO_INDEX_PATH),
            ('TICKER_TO_INDEX_PATH', settings.TICKER_TO_INDEX_PATH),
        ]:
            if not Path(path).exists():
                logger.error(
                    '[%s] Required file %s (%s) does not exist. '
                    'Model will be UNAVAILABLE.',
                    config_key, label, path,
                )
                self._unavailable.add(config_key)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

        # Transformer variants — pick the right tokenizer class.
        resolved = model_params['resolved_weights']
        if resolved in _BERT_TOKENIZER_HF_IDS:
            tokenizer = BertTokenizer.from_pretrained(resolved)
        else:
            tokenizer = AutoTokenizer.from_pretrained(resolved)
        return get_preprocessor('transformer_model', tokenizer=tokenizer)

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self, config_key: str) -> None:
        """Load a model into the registry if not already present."""
        if config_key in self._managers:
            return

        with self._lock:
            if config_key in self._managers:
                return

            if config_key in self._unavailable:
                raise ModelConfigError(
                    f"Model '{config_key}' is unavailable — configuration "
                    f"validation failed at startup. Check logs for details."
                )

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> tuple[ModelManager, Any, str]:
        """
        Returns (model_manager, preprocessor, model_type) for a user-facing
        model ID such as 'FinBERT' or 'TweetBERT'.

        Raises ValueError if the model ID is unknown.
        Raises ModelConfigError if the model failed validation.
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
        """Models that passed config validation (may not be loaded yet)."""
        return [
            model_id for model_id, key in MODEL_ID_TO_CONFIG_KEY.items()
            if key not in self._unavailable
        ]

    @property
    def unavailable_models(self) -> list[str]:
        """Models that failed config validation."""
        return [
            model_id for model_id, key in MODEL_ID_TO_CONFIG_KEY.items()
            if key in self._unavailable
        ]

    @property
    def loaded_models(self) -> list[str]:
        return [
            model_id for model_id, key in MODEL_ID_TO_CONFIG_KEY.items()
            if key in self._managers
        ]
