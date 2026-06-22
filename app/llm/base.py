from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.llm.structured import build_schema_instruction, parse_structured_response
from app.llm.types import ChatResult, Message, Role, StructuredChatResult

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Базовая ошибка LLM-слоя."""


class LLMTransientError(LLMError):
    """Временная ошибка: 5xx, таймаут или сеть; можно повторять."""


class LLMPermanentError(LLMError):
    """Постоянная ошибка: 4xx или авторизация; повтор бессмысленен."""


class LLMParseError(LLMPermanentError):
    """Ответ модели не удалось распарсить или провалидировать."""


class LLMClient(ABC):
    provider: str

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ChatResult: ...

    async def chat_structured(
        self,
        messages: list[Message],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        max_parse_retries: int = 2,
    ) -> StructuredChatResult[T]:
        """Вызывает chat() и валидирует ответ как JSON по response_model."""
        schema_instruction = build_schema_instruction(response_model)
        augmented_messages = [schema_instruction, *messages]
        parse_error: LLMParseError | None = None

        for attempt in range(max_parse_retries):
            request_messages = list(augmented_messages)
            if attempt > 0:
                request_messages.append(
                    Message(
                        role=Role.USER,
                        content=(
                            "Your previous answer was invalid. "
                            "Return only valid JSON matching the schema."
                        ),
                    )
                )

            chat_result = await self.chat(
                request_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            try:
                data = parse_structured_response(chat_result.content, response_model)
            except LLMParseError as exc:
                parse_error = exc
                continue

            return StructuredChatResult(data=data, chat=chat_result)

        assert parse_error is not None
        raise parse_error

    @abstractmethod
    async def close(self) -> None: ...
