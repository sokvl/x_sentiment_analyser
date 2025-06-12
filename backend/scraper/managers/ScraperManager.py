from __future__ import annotations

import logging
import os
from threading import active_count
from threading import Thread

from scraper.scrapers.twitter_scraper import TwitterScraper


class ScraperManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scrapers = {}
        # Maksymalna liczba wątków zgodnie z liczbą dostępnych rdzeni procesora
        self.max_threads = os.cpu_count()

    def _set_scraper_wrapper(self, instance, source):
        try:
            instance.run_procedure()
        except Exception as e:
            self.logger.exception('Error in scraper for source %s', e)

    def get_scraper(self, source):
        """
        Returns a scraper instance for the given source or None if not found.
        """
        return self.scrapers.get(source, {}).get('scraper')

    def set_scraper(self, source):
        """
        Creates a new scraper for the given source and
        starts it in a separate thread.
        If a scraper for the source already exists, it will not create a new one.
        """
        if source in self.scrapers:
            self.logger.warning(
                'Scraper for source %s already exists.', source,
            )
            return

        current_threads = active_count()

        if current_threads >= self.max_threads:
            self.logger.error(
                'Cannot start new scraper. Maximum thread limit of %s reached.',
                self.max_threads,
            )
            return

        scraper_instance = TwitterScraper()
        self.scrapers[source] = {'scraper': scraper_instance, 'thread': None}

        thread = Thread(
            target=scraper_instance.run_procedure,
            name=f"{source}_scraper_thread", daemon=True,
        )
        thread.start()
        self.scrapers[source]['thread'] = thread

    def stop_scraper(self, source):
        """
        Stops the scraper (if running) for the specified source and removes it from the manager.
        """
        if source in self.scrapers:
            scraper_data = self.scrapers[source]
            scraper_instance = scraper_data['scraper']

            self.logger.info(
                'Attempting to stop scraper for source: %s...',
                source,
            )

            # Signal the scraper to stop (should be implemented in the scraper itself)
            scraper_instance.stop()
            scraper_data['thread'].join(timeout=5)

            del self.scrapers[source]
            self.logger.info(
                'Scraper for source %s has been removed from the manager.',
                source,
            )
        else:
            self.logger.warning('No scraper found for source %s.', source)

    def restart_scraper(self, source):
        """
        Restarts the scraper for a given source by stopping it first (if it exists)
        and then creating a new instance.
        """
        self.logger.info(
            'Restarting scraper for source: %s...',
            source,
        )
        # Step 1: Stop the existing scraper if it exists
        self.stop_scraper(source)

        # Step 2: Create a new scraper
        self.set_scraper(source)
        self.logger.info(
            'Scraper for source %s has been restarted.',
            source,
        )

    def access_scraper(self, source, method_name, *args, **kwargs):
        """
        Allows calling a method on the underlying scraper object for the specified source.
        Example usage:
            manager.access_scraper("my_source", "method_to_call", arg1, arg2, kwarg1=value1)
        """
        scraper = self.get_scraper(source)
        if not scraper:
            return {'error': f"Scraper for source '{source}' not found."}

        if not hasattr(scraper, method_name):
            return {'error': f"Method '{method_name}' not found on scraper '{source}'."}

        method = getattr(scraper, method_name)
        if callable(method):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                return {'error': f"Error during execution of method '{method_name}': {e}"}
        else:
            return {'error': f"'{method_name}' is not a callable method."}

    def find_and_update_scraper_config(self, source, config):
        """
        Updates the configuration for the specified scraper.
        Assumes that the scraper has a method 'update_config' implemented.
        Returns True if updated, False otherwise.
        """
        scraper = self.get_scraper(source)
        if scraper:
            try:
                scraper.update_config(config)
                print(f"Configuration for source {source} has been updated.")
                return True
            except Exception as e:
                print(f"Error updating configuration for {source}: {e}")
        return False
