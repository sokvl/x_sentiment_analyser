from __future__ import annotations

import json
import logging
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'

    def ready(self):
        logger = logging.getLogger(__name__)
        logger.debug('Starting ScraperConfig.ready()...')

        config_path = Path(settings.BASE_DIR) / 'scraper' / 'configs' / 'model_configs.json'
        with open(config_path) as file:
            model_configs = json.load(file)

        # --- Model Registry (lazy-loads models on first use) ---
        try:
            from .managers.model_registry import ModelRegistry

            logger.debug('Initializing MODEL_REGISTRY...')
            self.MODEL_REGISTRY = ModelRegistry(model_configs)
            logger.debug('MODEL_REGISTRY initialized.')
        except Exception:
            logger.exception('Failed to initialize MODEL_REGISTRY')

        # --- DataManager (uses the registry for model resolution) ---
        try:
            from .managers.data_manager.data_manager import DataManager

            logger.debug('Initializing DATA_MANAGER...')
            self.DATA_MANAGER = DataManager(
                model_registry=self.MODEL_REGISTRY,
                default_model_id=settings.DEFAULT_MODEL_ID,
            )
            logger.debug('DATA_MANAGER initialized.')
        except Exception:
            logger.exception('Failed to initialize DATA_MANAGER')

        # --- Scraper Manager ---
        try:
            from .managers.ScraperManager import ScraperManager

            logger.debug('Initializing SCRAPER_MANAGER...')
            self.SCRAPER_MANAGER = ScraperManager()
            logger.debug('SCRAPER_MANAGER initialized.')
        except Exception:
            logger.exception('Failed to initialize SCRAPER_MANAGER')

        logger.debug('ScraperConfig.ready() completed.')

        # Register signal handlers (e.g. Config cache invalidation)
        import scraper.signals  # noqa: F401
