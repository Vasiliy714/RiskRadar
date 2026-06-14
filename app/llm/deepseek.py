import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import DeepSeekSettings
from app.llm.base import LLMClient, LLMPermanentError, LLMTransientError
from app.llm.types import ChatResult, Message, TokenUsage


class DeepSeekClient(LLMClient):
    provider = "deepseek"

    def __init__(
        self,
        settings: DeepSeekSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if settings.api_key is None:
            msg = "DEEPSEEK_API_KEY is required for DeepSeekClient"
            raise ValueError(msg)

        self._settings = settings
        self._model = settings.model

        if http_client is not None:
            self._client = http_client
        else:
            self._client = httpx.AsyncClient(
                base_url=settings.base_url,
                timeout=httpx.Timeout(settings.timeout_seconds, connect=10.0),
                headers={
                    "Authorization": f"Bearer {settings.api_key.get_secret_value()}",
                },
            )

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
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data, latency_ms = await self._post_with_retry("/v1/chat/completions", payload)

        choice = data["choices"][0]
        usage = data["usage"]
        return ChatResult(
            content=choice["message"]["content"],
            usage=TokenUsage(
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
            ),
            model=data["model"],
            provider=self.provider,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _do_post(
        self,
        path: str,
        payload: dict[str, object],
    ) -> tuple[dict[str, Any], float]:
        start = time.perf_counter()
        try:
            resp = await self._client.post(path, json=payload)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise LLMTransientError(f"deepseek network error: {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code >= 500:
            raise LLMTransientError(f"deepseek 5xx: {resp.status_code}")
        if resp.status_code == 429:
            raise LLMTransientError("deepseek rate limited")
        if resp.status_code >= 400:
            raise LLMPermanentError(
                f"deepseek {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json(), latency_ms

    async def _post_with_retry(
        self,
        path: str,
        payload: dict[str, object],
    ) -> tuple[dict[str, Any], float]:
        @retry(
            retry=retry_if_exception_type(LLMTransientError),
            stop=stop_after_attempt(self._settings.max_retries),
            wait=wait_exponential(multiplier=0.5, max=8),
            reraise=True,
        )
        async def _attempt() -> tuple[dict[str, Any], float]:
            return await self._do_post(path, payload)

        return await _attempt()
