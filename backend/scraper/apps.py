from __future__ import annotations

import json
import logging
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings

from .managers.data_manager.data_manager import DataManager
from .managers.model_manager.model_manager import ModelManager
from .managers.ScraperManager import ScraperManager
# from .managers.DataManager import DataManager
# from .managers.ModelManger import ModelManager

temp_vocab = {
    'vocab_size': 63175,
    'embedding_dim': 256,
    'lstm_hidden_dim': 256,
    'num_classes': 3,
    'ticker_vocab_size': 5,
    'dropout': 0.8,
}


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'

    def ready(self):
        logger = logging.getLogger(__name__)
        logger.debug('Starting ScraperConfig.ready()...')

        config_path = Path(settings.BASE_DIR) / 'scraper' / \
            'configs' / 'model_configs.json'
        with open(config_path) as file:
            model_configs = json.load(file)

        config = model_configs[settings.DEFAULT_MODEL]
        logger.debug(config)
        if config['model_lib'] == 'pytorch':
            # I will deal with this later
            pass
        else:
            model_name = config['model_name']
            model_params = config['params']

        try:
            logger.debug('Initializing LSTM_MODEL_MANAGER...')
            self.LSTM_MODEL_MANAGER = ModelManager(model_name, model_params)
            logger.debug(
                'LSTM_MODEL_MANAGER initialized: %s',
                self.LSTM_MODEL_MANAGER,
            )
        except Exception:
            logger.exception('Failed to initialize LSTM_MODEL_MANAGER')

        try:
            logger.debug('Initializing DATA_MANAGER...')
            self.DATA_MANAGER = DataManager(
                model_bundle={
                    'model_type': model_name,
                    'model_params': model_params,
                },
            )
            logger.debug(
                'DATA_MANAGER initialized: %s',
                self.DATA_MANAGER,
            )
        except Exception:
            logger.exception('Failed to initialize DATA_MANAGER')

        try:
            logger.debug('Initializing SCRAPER_MANAGER...')
            self.SCRAPER_MANAGER = ScraperManager()
            logger.debug(
                'SCRAPER_MANAGER initialized: %s',
                self.SCRAPER_MANAGER,
            )
        except Exception:
            logger.exception('Failed to initialize SCRAPER_MANAGER')

        logger.debug('ScraperConfig.ready() completed.')
