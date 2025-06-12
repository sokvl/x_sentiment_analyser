from __future__ import annotations

import datetime
import threading
from abc import ABC
from abc import abstractmethod
from collections import deque
from enum import Enum


class LogTypes(Enum):
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    MESSAGE = 'MESSAGE'
    DEBUG = 'DEBUG'


class ScraperStates(Enum):
    IDLE = 0
    SETTING_UP = 1
    RUNNING = 2
    PAUSED = 3
    STOPPED = 4


class Scraper(ABC):
    def __init__(self, config):
        self.config = config
        self.state = ScraperStates.IDLE
        self.logs = deque(maxlen=1000)
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.current_task = {}

    @abstractmethod
    def run_procedure(self) -> None:
        pass

    def pause(self) -> None:
        self._set_status(ScraperStates.PAUSED)
        self.pause_event.set()
        return

    def resume(self):
        self._set_status(ScraperStates.RUNNING)
        self.pause_event.clear()
        return

    def stop(self):
        self._set_status(ScraperStates.STOPPED)
        self.stop_event.set()
        return

    def update_config(self, config):
        self.config = config
        self._log(LogTypes.MESSAGE, f"Config updated.")

    def _log(self, log_type, message):
        time_stamp = datetime.datetime.now()
        self.logs.append(f"[{log_type.value}]:{time_stamp}: {message}")

    def _set_status(self, new_state):
        self.state = new_state
        self._log(LogTypes.MESSAGE, f"State changed: {new_state}")

    def _update_task(self, new_task, overwrite=False):
        """
        Updates the current task.

        Parameters:
        - new_task: dict containing the new task values.
        - overwrite: If True, replaces the entire task. If False, updates only the specified keys.
        """
        if overwrite:
            self._log(LogTypes.MESSAGE, f"Task Overwritten: {new_task}")
            self.current_task = new_task
        else:
            if not isinstance(self.current_task, dict):
                self.current_task = {}  # Inicjalizacja na wypadek braku taska
            self.current_task.update(new_task)

    def get_state(self) -> dict:
        return {
            'state': ScraperStates(self.state).name,
            'logs': self.logs,
            'current_task_details': self.current_task,
        }
