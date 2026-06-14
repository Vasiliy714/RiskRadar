from dataclasses import dataclass

from app.core.config import Settings
from app.core.db import DatabaseClient
from app.core.logging import get_logger
from app.core.qdrant import QdrantStore
from app.core.redis import RedisClient
from app.llm.base import LLMClient
from app.llm.deepseek import DeepSeekClient
from app.llm.instrumentation import InstrumentedLLMClient
from app.llm.mock import MockLLMClient

log = get_logger(__name__)


@dataclass(slots=True)
class AppClients:
    db: DatabaseClient
    redis: RedisClient
    qdrant: QdrantStore
    llm: LLMClient


def create_clients(settings: Settings, *, db_echo: bool = False) -> AppClients:
    return AppClients(
        db=DatabaseClient(settings.postgres.url, echo=db_echo),
        redis=RedisClient(settings.redis.url),
        qdrant=QdrantStore(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            grpc_port=settings.qdrant.grpc_port,
        ),
        llm=_create_llm(settings),
    )


def _create_llm(settings: Settings) -> LLMClient:
    inner: LLMClient
    match settings.app.llm_provider:
        case "mock":
            inner = MockLLMClient()
        case "deepseek":
            if settings.deepseek.api_key is None:
                msg = "DEEPSEEK_API_KEY is required when APP_LLM_PROVIDER=deepseek"
                raise ValueError(msg)
            inner = DeepSeekClient(settings.deepseek)
        case _:
            msg = f"Unknown LLM provider: {settings.app.llm_provider!r}"
            raise ValueError(msg)

    return InstrumentedLLMClient(inner)


async def shutdown_clients(clients: AppClients) -> None:
    for name, client in (
        ("llm", clients.llm),
        ("qdrant", clients.qdrant),
        ("redis", clients.redis),
        ("db", clients.db),
    ):
        try:
            await client.close()
        except Exception as exc:
            log.error("infra.close_failed", client=name, error=str(exc) or type(exc).__name__)
