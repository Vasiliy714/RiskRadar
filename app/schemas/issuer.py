from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IssuerBase(BaseModel):
    code: str = Field(min_length=1, max_length=32, examples=["SBER"])
    name: str = Field(min_length=1, max_length=512, examples=["Сбербанк"])
    inn: str | None = Field(
        default=None,
        max_length=12,
        pattern=r"^\d{10}|\d{12}$",
    )
    is_public: bool = True
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    sector: str | None = Field(default=None, max_length=128)


class IssuerCreate(IssuerBase):
    """Контракт на создание"""


class IssuerUpdate(BaseModel):
    """Контракт на частичное обновление — все поля опциональны."""

    name: str | None = Field(default=None, min_length=1, max_length=512)
    inn: str | None = Field(
        default=None,
        max_length=12,
        pattern=r"^\d{10}|\d{12}$",
    )
    is_public: bool | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    sector: str | None = Field(default=None, max_length=128)


class IssuerRead(IssuerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
