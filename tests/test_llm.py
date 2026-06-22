
import httpx
import pytest
from pydantic import SecretStr

from app.core.config import DeepSeekSettings, get_settings
from app.llm.base import LLMPermanentError, LLMTransientError
from app.llm.deepseek import DeepSeekClient
from app.llm.mock import MockLLMClient
from app.llm.types import Message, Role


def _settings(*, max_retries: int = 3) -> DeepSeekSettings:
    return DeepSeekSettings(
        api_key=SecretStr("test-key"),
        max_retries=max_retries,
    )


async def test_mock_llm_chat_returns_result() -> None:
    client = MockLLMClient(canned_response="hello world")
    result = await client.chat([Message(role=Role.USER, content="hi there")])
    assert result.content == "hello world"
    assert result.usage.completion_tokens == 2
    assert result.usage.total_tokens == result.usage.prompt_tokens + 2
    assert result.provider == "mock"


async def test_deepseek_500_raises_transient_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="https://api.deepseek.com",
        transport=transport,
    )
    client = DeepSeekClient(_settings(max_retries=3), http_client=http_client)
    try:
        with pytest.raises(LLMTransientError):
            await client.chat([Message(role=Role.USER, content="hi")])
    finally:
        await client.close()


async def test_deepseek_400_raises_permanent_error_without_retry() -> None:
    calls = 0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, text="bad request")
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="https://api.deepseek.com",
        transport=transport,
    )
    client = DeepSeekClient(_settings(max_retries=3), http_client=http_client)
    try:
        with pytest.raises(LLMPermanentError):
            await client.chat([Message(role=Role.USER, content="hi")])
        assert calls == 1  # tenacity не должен повторять постоянные ошибки
    finally:
        await client.close()


def _deepseek_configured() -> bool:
    return get_settings().deepseek.api_key is not None


@pytest.mark.integration
@pytest.mark.skipif(
    not _deepseek_configured(),
    reason="DEEPSEEK_API_KEY not set in .env",
)
async def test_deepseek_real_chat() -> None:
    settings = get_settings()
    client = DeepSeekClient(settings.deepseek)
    try:
        result = await client.chat(
            [Message(role=Role.USER, content="Ответь одним словом: тест")],
            max_tokens=16,
        )
        assert result.content.strip()
        assert result.provider == "deepseek"
        assert result.model
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0
        assert result.latency_ms > 0
    except LLMPermanentError as exc:
        if "402" in str(exc) and "Insufficient Balance" in str(exc):
            pytest.skip("DeepSeek account has no balance")
        raise
    finally:
        await client.close()
