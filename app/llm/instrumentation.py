import time

from app.llm.base import LLMClient, LLMPermanentError, LLMTransientError
from app.llm.types import ChatResult, Message
from app.observability.metrics import (
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
)


class InstrumentedLLMClient(LLMClient):
    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self.provider = inner.provider

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult:
        model_label = getattr(self._inner, "_model", "unknown")

        start = time.perf_counter()
        try:
            result = await self._inner.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMPermanentError:
            elapsed = time.perf_counter() - start
            LLM_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=model_label,
                outcome="permanent_error",
            ).inc()
            LLM_REQUEST_DURATION_SECONDS.labels(
                provider=self.provider,
                model=model_label,
            ).observe(elapsed)
            raise
        except LLMTransientError:
            elapsed = time.perf_counter() - start
            LLM_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=model_label,
                outcome="transient_error",
            ).inc()
            LLM_REQUEST_DURATION_SECONDS.labels(
                provider=self.provider,
                model=model_label,
            ).observe(elapsed)
            raise

        model_label = result.model
        elapsed = time.perf_counter() - start

        LLM_REQUESTS_TOTAL.labels(
            provider=result.provider,
            model=model_label,
            outcome="success",
        ).inc()
        LLM_REQUEST_DURATION_SECONDS.labels(
            provider=result.provider,
            model=model_label,
        ).observe(elapsed)
        LLM_TOKENS_TOTAL.labels(
            provider=result.provider,
            model=model_label,
            direction="prompt",
        ).inc(result.usage.prompt_tokens)
        LLM_TOKENS_TOTAL.labels(
            provider=result.provider,
            model=model_label,
            direction="completion",
        ).inc(result.usage.completion_tokens)
        return result

    async def close(self) -> None:
        await self._inner.close()
