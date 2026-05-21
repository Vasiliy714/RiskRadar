from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    log.info(
        "app.starting",
        env=settings.env,
        log_format=settings.log_format,
        log_level=settings.log_level,
    )
    yield
    log.info("app.stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RiskRadar",
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
