from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from app.llm.types import Message, Role

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)


def extract_json_text(content: str) -> str:
    """Извлекает JSON из обычного текста или markdown-блоков кода."""
    stripped = content.strip()
    match = _JSON_FENCE_RE.search(stripped)
    if match is not None:
        return match.group(1).strip()
    return stripped


def build_schema_instruction(response_model: type[BaseModel]) -> Message:
    schema_json = json.dumps(
        response_model.model_json_schema(),
        ensure_ascii=False,
    )
    return Message(
        role=Role.SYSTEM,
        content=(
            "Respond with a single valid JSON object that matches this schema. "
            "Do not include markdown fences or any text outside JSON.\n"
            f"{schema_json}"
        ),
    )


def parse_structured_response[T: BaseModel](content: str, response_model: type[T]) -> T:
    """Парсит и валидирует текст LLM как JSON в Pydantic-модель."""
    from app.llm.base import LLMParseError

    try:
        payload = json.loads(extract_json_text(content))
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON in model response: {exc.msg}"
        raise LLMParseError(msg) from exc

    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        msg = f"response JSON does not match schema: {exc.errors()[:3]}"
        raise LLMParseError(msg) from exc
