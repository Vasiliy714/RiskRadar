from __future__ import annotations

from app.llm.base import LLMClient
from app.llm.types import ChatResult, Message, TokenUsage


class MockLLMClient(LLMClient):
    provider = "mock"

    def __init__(self, canned_response: str = "MOCK_RESPONSE") -> None:
        self._canned = canned_response
        self._model = "mock-model"

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        prompt_text = " ".join(m.content for m in messages)
        prompt_tokens = len(prompt_text.split())
        completion_tokens = len(self._canned.split())

        return ChatResult(
            content=self._canned,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            model=self._model,
            provider=self.provider,
            latency_ms=0.0,
        )

    async def close(self) -> None:
        return None
