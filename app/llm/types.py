from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ChatResult(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float = Field(ge=0.0)
    finish_reason: str | None = None


__all__ = [
    "ChatResult",
    "Message",
    "Role",
    "TokenUsage",
]
