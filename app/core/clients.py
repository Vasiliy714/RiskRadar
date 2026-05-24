from dataclasses import dataclass

from app.core.config import Settings
from app.core.db import DatabaseClient
from app.core.logging import get_logger
from app.core.qdrant import QdrantStore
from app.core.redis import RedisClient

log = get_logger(__name__)


@dataclass(slots=True)
class AppClients:
    db: DatabaseClient
    redis: RedisClient
    qdrant: QdrantStore


def create_clients(settings: Settings, *, db_echo: bool = False) -> AppClients:
    return AppClients(
        db=DatabaseClient(settings.postgres.url, echo=db_echo),
        redis=RedisClient(settings.redis.url),
        qdrant=QdrantStore(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            grpc_port=settings.qdrant.grpc_port,
        ),
    )


async def shutdown_clients(clients: AppClients) -> None:
    for name, client in (
        ("qdrant", clients.qdrant),
        ("redis", clients.redis),
        ("db", clients.db),
    ):
        try:
            await client.close()
        except Exception as exc:
            log.error("infra.close_failed", client=name, error=str(exc) or type(exc).__name__)
