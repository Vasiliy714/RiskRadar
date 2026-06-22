from __future__ import annotations

import pytest

from app.llm.base import LLMTransientError
from app.llm.circuit_breaker import CircuitBreakerLLMClient
from app.llm.mock import MockLLMClient
from app.llm.types import ChatResult, Message, Role


class _FailingClient(MockLLMClient):
    provider = "failing"

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        self.calls += 1
        raise LLMTransientError("provider down")


class _FlakyClient(MockLLMClient):
    provider = "flaky"

    def __init__(self) -> None:
        super().__init__(canned_response="ok")
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        self.calls += 1
        if self.calls == 1:
            raise LLMTransientError("flaky")
        return await super().chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )


async def test_circuit_breaker_opens_after_threshold() -> None:
    inner = _FailingClient()
    cb = CircuitBreakerLLMClient(
        inner,
        failure_threshold=3,
        cooldown_seconds=60.0,
    )
    try:
        for _ in range(3):
            with pytest.raises(LLMTransientError, match="provider down"):
                await cb.chat([Message(role=Role.USER, content="hi")])
        assert inner.calls == 3

        with pytest.raises(LLMTransientError, match="circuit open"):
            await cb.chat([Message(role=Role.USER, content="hi")])
        assert inner.calls == 3
    finally:
        await cb.close()


async def test_circuit_breaker_success_resets_failures() -> None:
    inner = _FlakyClient()
    cb = CircuitBreakerLLMClient(inner, failure_threshold=2, cooldown_seconds=60.0)
    try:
        with pytest.raises(LLMTransientError, match="flaky"):
            await cb.chat([Message(role=Role.USER, content="hi")])

        result = await cb.chat([Message(role=Role.USER, content="hi")])
        assert result.content == "ok"
        assert inner.calls == 2
    finally:
        await cb.close()
