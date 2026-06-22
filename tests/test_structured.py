from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from app.llm.base import LLMParseError
from app.llm.mock import MockLLMClient
from app.llm.structured import extract_json_text, parse_structured_response
from app.llm.types import ChatResult, Message, Role


class RiskSummary(BaseModel):
    issuer_code: str
    risk_level: str = Field(pattern=r"^(low|medium|high|critical)$")
    summary: str


async def test_mock_chat_structured_returns_valid_model() -> None:
    client = MockLLMClient(
        structured_payload={
            "issuer_code": "SBER",
            "risk_level": "medium",
            "summary": "Stable issuer with moderate market risk.",
        }
    )
    try:
        result = await client.chat_structured(
            [Message(role=Role.USER, content="analyze")],
            RiskSummary,
        )
        assert result.data.issuer_code == "SBER"
        assert result.data.risk_level == "medium"
        assert result.chat.provider == "mock"
    finally:
        await client.close()


async def test_chat_structured_retries_on_invalid_json() -> None:
    class FlakyMock(MockLLMClient):
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
            if self.calls == 1:
                return await super().chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            self._structured_payload = {
                "issuer_code": "GAZP",
                "risk_level": "high",
                "summary": "Elevated leverage risk.",
            }
            return await super().chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    client = FlakyMock()
    try:
        result = await client.chat_structured(
            [Message(role=Role.USER, content="analyze")],
            RiskSummary,
            max_parse_retries=2,
        )
        assert result.data.issuer_code == "GAZP"
        assert client.calls == 2
    finally:
        await client.close()


def test_extract_json_text_from_markdown_fence() -> None:
    raw = '```json\n{"answer": "ok"}\n```'
    assert extract_json_text(raw) == '{"answer": "ok"}'


def test_parse_structured_response_raises_on_schema_mismatch() -> None:
    class Answer(BaseModel):
        answer: str

    with pytest.raises(LLMParseError):
        parse_structured_response('{"answer": 123}', Answer)


def test_parse_structured_response_validates_model() -> None:
    class Answer(BaseModel):
        answer: str

    parsed = parse_structured_response('{"answer": "ok"}', Answer)
    assert parsed.answer == "ok"
