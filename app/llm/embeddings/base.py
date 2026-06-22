from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingsError(Exception):
    """Базовая ошибка провайдеров эмбеддингов."""


class EmbeddingsTransientError(EmbeddingsError):
    """Временная ошибка эмбеддингов: сеть, 5xx или лимит запросов."""


class EmbeddingsPermanentError(EmbeddingsError):
    """Постоянная ошибка эмбеддингов: авторизация или некорректный запрос."""


class EmbeddingsProvider(ABC):
    provider: str
    model: str
    vector_size: int

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]: ...

    @abstractmethod
    async def close(self) -> None: ...
