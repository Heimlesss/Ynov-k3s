from abc import ABC, abstractmethod

# Abstract base class for all connectors
class Connector(ABC):
    def __init__(self, url):
        self.url = url

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass