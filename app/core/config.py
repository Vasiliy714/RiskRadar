from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        env_prefix = "APP_",
        extra = "ignore",
    )

    env: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"
    log_format: Literal["pretty", "json"] = "pretty"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if normalized not in allowed:
            msg = f"log_level must be one of {sorted(allowed)}, got {value!r}"
            raise ValueError(msg)
        return normalized

    @property
    def is_local(self) -> bool:
        return self.env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
