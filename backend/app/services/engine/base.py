import logging
from abc import ABC, abstractmethod


class BaseEngine(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass
