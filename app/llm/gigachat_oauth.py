from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import GigaChatSettings
from app.llm.base import LLMPermanentError, LLMTransientError

_NETWORK_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
)


def gigachat_verify_setting(settings: GigaChatSettings) -> str | bool:
    if not settings.verify_ssl:
        return False  # только для локальной разработки; в prod используйте GIGACHAT_CA_BUNDLE
    if settings.ca_bundle:
        return settings.ca_bundle
    return True


class GigaChatHttpSession:
    """Общий кэш OAuth-токена и авторизованные POST-запросы к REST API GigaChat."""

    def __init__(
        self,
        settings: GigaChatSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if settings.auth_key is None:
            msg = "GIGACHAT_AUTH_KEY is required for GigaChat API"
            raise ValueError(msg)

        self._settings = settings
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._token_lock = asyncio.Lock()

        timeout = httpx.Timeout(settings.timeout_seconds, connect=10.0)
        verify = gigachat_verify_setting(settings)

        if http_client is not None:
            self._oauth_client = http_client
            self._api_client = http_client
        else:
            self._oauth_client = httpx.AsyncClient(verify=verify, timeout=timeout)
            self._api_client = httpx.AsyncClient(
                base_url=settings.base_url,
                verify=verify,
                timeout=timeout,
            )

    async def close(self) -> None:
        if self._oauth_client is self._api_client:
            await self._oauth_client.aclose()
            return
        await self._oauth_client.aclose()
        await self._api_client.aclose()

    async def post_with_retry(
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

    async def _ensure_token(self) -> str:
        async with self._token_lock:
            now = time.time()
            if self._token is None or now >= self._expires_at - 60:
                await self._fetch_token()
            assert self._token is not None
            return self._token

    async def _fetch_token(self) -> None:
        auth_key = self._settings.auth_key
        assert auth_key is not None
        try:
            resp = await self._oauth_client.post(
                self._settings.oauth_url,
                headers={
                    "Authorization": f"Basic {auth_key.get_secret_value()}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": self._settings.scope},
            )
        except _NETWORK_ERRORS as exc:
            raise LLMTransientError(f"gigachat oauth network error: {exc}") from exc

        if resp.status_code >= 500:
            raise LLMTransientError(f"gigachat oauth 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            raise LLMPermanentError(
                f"gigachat oauth {resp.status_code}: {resp.text[:200]}"
            )

        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = body["expires_at"] / 1000

    async def _do_post(
        self,
        path: str,
        payload: dict[str, object],
    ) -> tuple[dict[str, Any], float]:
        token = await self._ensure_token()
        start = time.perf_counter()
        try:
            resp = await self._api_client.post(
                path,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        except _NETWORK_ERRORS as exc:
            raise LLMTransientError(f"gigachat network error: {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code == 401:
            async with self._token_lock:
                self._token = None
            await self._fetch_token()
            token = await self._ensure_token()
            try:
                resp = await self._api_client.post(
                    path,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except _NETWORK_ERRORS as exc:
                raise LLMTransientError(f"gigachat network error: {exc}") from exc
            latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code >= 500:
            raise LLMTransientError(f"gigachat 5xx: {resp.status_code}")
        if resp.status_code == 429:
            raise LLMTransientError("gigachat rate limited")
        if resp.status_code >= 400:
            raise LLMPermanentError(
                f"gigachat {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json(), latency_ms
