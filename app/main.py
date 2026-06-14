from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.api.v1.router import api_v1_router
from app.core.clients import create_clients, shutdown_clients
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.app)

    log.info(
        "app.starting",
        env=settings.app.env,
        log_format=settings.app.log_format,
        log_level=settings.app.log_level,
    )

    clients = create_clients(
        settings,
        db_echo=settings.app.db_echo or settings.app.is_local,
    )
    app.state.clients = clients

    log.info("infra.initialized")

    try:
        yield
    finally:
        log.info("app.stopping")
        await shutdown_clients(clients)
        log.info("app.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RiskRadar",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(api_v1_router)

    return app


app = create_app()
