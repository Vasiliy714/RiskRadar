from fastapi import APIRouter, Depends, Response, status

from app.core.clients import AppClients
from app.core.config import get_settings
from app.core.deps import get_clients
from app.core.health import CheckStatus, ReadinessResponse, run_readiness_checks

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/readyz", response_model=ReadinessResponse)
async def readyz(
    response: Response,
    clients: AppClients = Depends(get_clients),  # noqa: B008
) -> ReadinessResponse:
    settings = get_settings()
    result = await run_readiness_checks(
        clients,
        expose_error_details=settings.app.expose_error_details
    )
    if result.status != CheckStatus.UP:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
