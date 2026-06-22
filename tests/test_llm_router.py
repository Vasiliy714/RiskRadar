from __future__ import annotations

import pytest

from app.llm.base import LLMError, LLMPermanentError, LLMTransientError
from app.llm.mock import MockLLMClient
from app.llm.router import LLMRouter
from app.llm.types import ChatResult, Message, Role


class _TransientFailClient(MockLLMClient):
    provider = "primary-fail"

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        raise LLMTransientError("primary unavailable")


class _PermanentFailClient(MockLLMClient):
    provider = "primary-permanent"

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        raise LLMPermanentError("bad request")


async def test_router_falls_back_on_transient_error() -> None:
    primary = _TransientFailClient()
    fallback = MockLLMClient(canned_response="fallback-ok")
    router = LLMRouter(primary, [fallback])
    try:
        result = await router.chat([Message(role=Role.USER, content="hi")])
        assert result.content == "fallback-ok"
        assert result.provider == "mock"
    finally:
        await router.close()


async def test_router_fail_fast_on_permanent_error() -> None:
    primary = _PermanentFailClient()
    fallback = MockLLMClient(canned_response="never-used")
    router = LLMRouter(primary, [fallback])
    try:
        with pytest.raises(LLMPermanentError, match="bad request"):
            await router.chat([Message(role=Role.USER, content="hi")])
    finally:
        await router.close()


async def test_router_raises_when_all_providers_exhausted() -> None:
    primary = _TransientFailClient()
    fallback = _TransientFailClient()
    fallback.provider = "fallback-fail"
    router = LLMRouter(primary, [fallback])
    try:
        with pytest.raises(LLMError, match="all LLM providers exhausted"):
            await router.chat([Message(role=Role.USER, content="hi")])
    finally:
        await router.close()
