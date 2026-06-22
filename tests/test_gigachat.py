from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import GigaChatSettings
from app.llm.base import LLMPermanentError
from app.llm.gigachat import GigaChatClient
from app.llm.types import Message, Role


def _gigachat_settings(*, max_retries: int = 3) -> GigaChatSettings:
    return GigaChatSettings(
        auth_key=SecretStr("test-auth-key"),
        verify_ssl=False,
        max_retries=max_retries,
    )


async def test_gigachat_chat_returns_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "expires_at": 4_000_000_000_000,
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "GigaChat",
                "choices": [
                    {
                        "message": {"content": "ответ"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 1,
                    "total_tokens": 4,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        transport=transport,
    )
    client = GigaChatClient(_gigachat_settings(), http_client=http_client)
    try:
        result = await client.chat([Message(role=Role.USER, content="привет")])
        assert result.content == "ответ"
        assert result.provider == "gigachat"
        assert result.usage.total_tokens == 4
    finally:
        await client.close()


async def test_gigachat_oauth_401_raises_permanent_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        transport=transport,
    )
    client = GigaChatClient(_gigachat_settings(max_retries=1), http_client=http_client)
    try:
        with pytest.raises(LLMPermanentError):
            await client.chat([Message(role=Role.USER, content="hi")])
    finally:
        await client.close()


def _gigachat_configured() -> bool:
    from app.core.config import get_settings

    return get_settings().gigachat.auth_key is not None


@pytest.mark.integration
@pytest.mark.skipif(
    not _gigachat_configured(),
    reason="GIGACHAT_AUTH_KEY not set in .env",
)
async def test_gigachat_real_chat() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    client = GigaChatClient(settings.gigachat)
    try:
        result = await client.chat(
            [Message(role=Role.USER, content="Ответь одним словом: тест")],
            max_tokens=16,
        )
        assert result.content.strip()
        assert result.provider == "gigachat"
        assert result.usage.total_tokens > 0
    finally:
        await client.close()
