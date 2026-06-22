from __future__ import annotations

import asyncio
import time
from enum import StrEnum

from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMTransientError
from app.llm.types import ChatResult, Message
from app.observability.metrics import CIRCUIT_BREAKER_STATE

log = get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


_STATE_GAUGE: dict[CircuitState, int] = {
    CircuitState.CLOSED: 0,
    CircuitState.OPEN: 1,
    CircuitState.HALF_OPEN: 2,
}


class CircuitBreakerLLMClient(LLMClient):
    def __init__(
        self,
        inner: LLMClient,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._inner = inner
        self.provider = inner.provider
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._lock = asyncio.Lock()
        self._set_state(CircuitState.CLOSED)

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at < self._cooldown_seconds:
                    raise LLMTransientError(f"{self.provider} circuit open")
                self._set_state(CircuitState.HALF_OPEN)

        try:
            result = await self._inner.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMTransientError:
            await self._on_failure()
            raise

        await self._on_success()
        return result

    async def close(self) -> None:
        await self._inner.close()

    async def _on_success(self) -> None:
        async with self._lock:
            self._failures = 0
            if self._state != CircuitState.CLOSED:
                self._set_state(CircuitState.CLOSED)

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN or self._failures >= self._failure_threshold:
                self._open()

    def _open(self) -> None:
        self._opened_at = time.monotonic()
        self._set_state(CircuitState.OPEN)
        log.warning(
            "circuit_breaker.opened",
            provider=self.provider,
            failures=self._failures,
        )

    def _set_state(self, state: CircuitState) -> None:
        self._state = state
        CIRCUIT_BREAKER_STATE.labels(provider=self.provider).set(
            _STATE_GAUGE[state]
        )
