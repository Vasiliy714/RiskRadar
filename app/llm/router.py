from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMError, LLMPermanentError, LLMTransientError
from app.llm.types import ChatResult, Message, StructuredChatResult
from app.observability.metrics import LLM_FALLBACKS_TOTAL

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMRouter(LLMClient):
    provider = "router"

    def __init__(self, primary: LLMClient, fallbacks: list[LLMClient]) -> None:
        self._chain = [primary, *fallbacks]

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        last_exc: Exception | None = None
        for i, client in enumerate(self._chain):
            try:
                result = await client.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except LLMTransientError as exc:
                last_exc = exc
                log.warning(
                    "llm.fallback",
                    from_provider=client.provider,
                    error=str(exc),
                )
                continue
            except LLMPermanentError:
                raise
            else:
                if i > 0:
                    LLM_FALLBACKS_TOTAL.labels(
                        from_provider=self._chain[i - 1].provider,
                        to_provider=client.provider,
                    ).inc()
                return result

        raise LLMError("all LLM providers exhausted") from last_exc

    async def chat_structured(
        self,
        messages: list[Message],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        max_parse_retries: int = 2,
    ) -> StructuredChatResult[T]:
        last_exc: Exception | None = None
        for i, client in enumerate(self._chain):
            try:
                result = await client.chat_structured(
                    messages,
                    response_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    max_parse_retries=max_parse_retries,
                )
            except LLMTransientError as exc:
                last_exc = exc
                log.warning(
                    "llm.fallback",
                    from_provider=client.provider,
                    error=str(exc),
                )
                continue
            except LLMPermanentError:
                raise
            else:
                if i > 0:
                    LLM_FALLBACKS_TOTAL.labels(
                        from_provider=self._chain[i - 1].provider,
                        to_provider=client.provider,
                    ).inc()
                return result

        raise LLMError("all LLM providers exhausted") from last_exc

    async def close(self) -> None:
        for client in self._chain:
            await client.close()
