from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    llm_provider: Literal["mock", "deepseek", "gigachat", "router"] = "mock"
    llm_cb_failure_threshold: int = Field(default=5, ge=1)
    llm_cb_cooldown_seconds: float = Field(default=30.0, gt=0)
    llm_parse_max_retries: int = Field(default=2, ge=1)
    embeddings_provider: Literal["mock", "local", "gigachat"] = "mock"
    embeddings_model: str | None = None
    embeddings_batch_size: int = Field(default=32, ge=1, le=256)
    rag_chunk_size: int = Field(default=800, ge=100, le=4000)
    rag_chunk_overlap: int = Field(default=150, ge=0, le=1000)
    rag_hybrid_enabled: bool = True
    rag_search_prefetch_limit: int = Field(default=50, ge=1, le=200)
    rag_news_decay_half_life_days: float = Field(default=90.0, gt=0)

    env: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"
    log_format: Literal["pretty", "json"] = "pretty"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    db_echo: bool = False

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

    @property
    def expose_error_details(self) -> bool:
        return self.env in ("local", "dev")


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="POSTGRES_",
        extra="ignore",
    )

    user: str
    password: SecretStr
    db: str
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)

    @property
    def url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="REDIS_",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = Field(default=6379, ge=1, le=65535)
    password: SecretStr | None = None
    db: int = Field(default=0, ge=0)

    @property
    def url(self) -> str:
        if self.password is not None:
            pwd = self.password.get_secret_value()
            return f"redis://:{pwd}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QDRANT_",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = Field(default=6333, ge=1, le=65535)
    grpc_port: int = Field(default=6334, ge=1, le=65535)
    collection_name: str = "riskradar_chunks"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class DeepSeekSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DEEPSEEK_",
        extra="ignore",
    )
    api_key: SecretStr | None = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    timeout_seconds: float = 60.0
    max_retries: int = 3


class GigaChatSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GIGACHAT_",
        extra="ignore",
    )
    auth_key: SecretStr | None = None
    scope: str = "GIGACHAT_API_PERS"
    model: str = "GigaChat"
    oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    ca_bundle: str | None = None
    verify_ssl: bool = True
    timeout_seconds: float = 60.0
    max_retries: int = 3
    embeddings_model: str = "Embeddings"


class Settings:
    """Корневой контейнер настроек (не BaseSettings)."""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.postgres = PostgresSettings()
        self.redis = RedisSettings()
        self.qdrant = QdrantSettings()
        self.deepseek = DeepSeekSettings()
        self.gigachat = GigaChatSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
