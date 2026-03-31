from __future__ import annotations

import logging
import os
from threading import active_count
from threading import Lock
from threading import Thread

from scraper.scrapers.twitter_scraper import TwitterScraper


class ScraperManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scrapers = {}
        self.lock = Lock()
        # Maksymalna liczba wątków zgodnie z liczbą dostępnych rdzeni procesora
        self.max_threads = os.cpu_count() or 4



    def get_scraper(self, source):
        """
        Returns a scraper instance for the given source or None if not found.
        """
        return self.scrapers.get(source, {}).get('scraper')

    def _start_thread(self, source, scraper_instance):
        thread = Thread(
            target=scraper_instance.run_procedure,
            name=f"{source}_scraper_thread",
            daemon=True,
        )
        thread.start()
        self.scrapers[source]['thread'] = thread

    def set_scraper(self, source):
        """
        Creates a new scraper for the given source and starts it in a separate thread.
        If a stopped scraper already exists its browser session is reused — login is skipped
        when the scraper detects it is already authenticated.
        """
        with self.lock:
            existing = self.scrapers.get(source)
            if existing:
                scraper_instance = existing['scraper']
                thread = existing.get('thread')
                if thread and thread.is_alive():
                    self.logger.warning('Scraper for source %s is already running.', source)
                    return
                # Reuse the stopped instance (keeps the browser session)
                self.logger.info('Reusing stopped scraper for source %s.', source)
                scraper_instance.reset()
                self._start_thread(source, scraper_instance)
                return

            if active_count() >= self.max_threads:
                self.logger.error(
                    'Cannot start new scraper. Maximum thread limit of %s reached.',
                    self.max_threads,
                )
                return

            scraper_instance = TwitterScraper()
            self.scrapers[source] = {'scraper': scraper_instance, 'thread': None}
            self._start_thread(source, scraper_instance)

    def stop_scraper(self, source):
        """
        Signals the scraper to stop and waits for the thread to finish.
        The scraper instance (and its browser session) is kept in the manager
        so it can be resumed without a fresh login.
        """
        with self.lock:
            if source not in self.scrapers:
                self.logger.warning('No scraper found for source %s.', source)
                return

            scraper_data = self.scrapers[source]
            scraper_instance = scraper_data['scraper']

            self.logger.info('Stopping scraper for source: %s...', source)
            if scraper_instance and hasattr(scraper_instance, 'stop'):
                scraper_instance.stop()
            thread = scraper_data.get('thread')
            if thread:
                thread.join(timeout=10)
            scraper_data['thread'] = None
            self.logger.info('Scraper for source %s stopped (browser session preserved).', source)

    def destroy_scraper(self, source):
        """
        Fully shuts down the scraper including its browser session and removes it from the manager.
        Use this when a clean slate is needed (e.g. credential change).
        """
        with self.lock:
            if source not in self.scrapers:
                self.logger.warning('No scraper found for source %s.', source)
                return
            scraper_data = self.scrapers[source]
            scraper_instance = scraper_data['scraper']
            if scraper_instance and hasattr(scraper_instance, 'stop'):
                scraper_instance.stop()
            thread = scraper_data.get('thread')
            if thread:
                thread.join(timeout=10)
            # Quit the browser
            instance = getattr(scraper_instance, 'instance', None)
            if instance:
                try:
                    instance.quit()
                except Exception:
                    pass
            del self.scrapers[source]
            self.logger.info('Scraper for source %s destroyed.', source)

    def restart_scraper(self, source):
        """
        Stops the scraper thread (preserving the browser) then restarts it.
        The scraper will skip login if it detects an active session.
        """
        self.logger.info('Restarting scraper for source: %s...', source)
        self.stop_scraper(source)
        self.set_scraper(source)
        self.logger.info('Scraper for source %s restarted.', source)

    def access_scraper(self, source, method_name, *args, **kwargs):
        """
        Allows calling a method on the underlying scraper object for the specified source.
        Example usage:
            manager.access_scraper("my_source", "method_to_call", arg1, arg2, kwarg1=value1)
        """
        scraper = self.get_scraper(source)
        if not scraper:
            raise ValueError(f"Scraper for source '{source}' not found.")

        if not hasattr(scraper, method_name):
            raise AttributeError(f"Method '{method_name}' not found on scraper '{source}'.")

        method = getattr(scraper, method_name)
        if callable(method):
            return method(*args, **kwargs)
        else:
            raise TypeError(f"'{method_name}' is not a callable method.")

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
                self.logger.info('Configuration for source %s updated.', source)
                return True
            except Exception:
                self.logger.exception('Error updating configuration for source %s', source)
        return False
