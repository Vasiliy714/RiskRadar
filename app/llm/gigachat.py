from __future__ import annotations

from typing import Any

import httpx

from app.core.config import GigaChatSettings
from app.llm.base import LLMClient
from app.llm.gigachat_oauth import GigaChatHttpSession
from app.llm.types import ChatResult, Message, TokenUsage


class GigaChatClient(LLMClient):
    provider = "gigachat"

    def __init__(
        self,
        settings: GigaChatSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._model = settings.model
        self._session = GigaChatHttpSession(settings, http_client=http_client)

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [m.model_dump(mode="json") for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data, latency_ms = await self._session.post_with_retry("/chat/completions", payload)
        return self._parse_chat_result(data, latency_ms)

    async def close(self) -> None:
        await self._session.close()

    def _parse_chat_result(self, data: dict[str, Any], latency_ms: float) -> ChatResult:
        choice = data["choices"][0]
        usage = data["usage"]
        return ChatResult(
            content=choice["message"]["content"],
            usage=TokenUsage(
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
            ),
            model=data.get("model", self._model),
            provider=self.provider,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )
