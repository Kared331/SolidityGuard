from abc import ABC, abstractmethod


class AbstractEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    def health_check(self) -> bool: ...
