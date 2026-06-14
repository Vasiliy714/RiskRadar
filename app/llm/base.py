from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.types import ChatResult, Message


class LLMError(Exception):
    """Базовая ошибка LLM-слоя."""


class LLMTransientError(LLMError):
    """Временная (5xx, timeout, сеть) — можно retry."""


class LLMPermanentError(LLMError):
    """Постоянная (4xx, auth) — retry бессмысленен."""


class LLMClient(ABC):
    provider: str

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult: ...

    @abstractmethod
    async def close(self) -> None: ...
