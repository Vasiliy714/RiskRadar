from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.clients import AppClients
from app.core.logging import get_logger

CHECK_TIMEOUT_SEC = 2.0

_REDACT_PATTERNS = (
    re.compile(r"postgresql(\+asyncpg)?://\S+", re.IGNORECASE),
    re.compile(r"redis://\S+", re.IGNORECASE),
    re.compile(r"(password|pwd|secret)[=:\s]+\S+", re.IGNORECASE),
)

log = get_logger(__name__)


class CheckStatus(StrEnum):
    UP = "up"
    DOWN = "down"


class DependencyCheck(BaseModel):
    status: CheckStatus
    latency_ms: float | None = None
    error: str | None = None
    error_type: str | None = None


class ReadinessResponse(BaseModel):
    status: CheckStatus
    checks: dict[str, DependencyCheck] = Field(default_factory=dict)


def _redact(message: str) -> str:
    redacted = message
    for pattern in _REDACT_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


def sanitize_error(exc: Exception, *, expose_error_details: bool) -> tuple[str, str]:
    error_type = type(exc).__name__
    if isinstance(exc, TimeoutError):
        return "timeout", error_type
    if expose_error_details:
        raw = str(exc).strip() or error_type
        return _redact(raw), error_type
    return error_type, error_type


async def _check(
    name: str,
    ping: Callable[[], Awaitable[None]],
    *,
    expose_error_details: bool,
) -> DependencyCheck:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(ping(), timeout=CHECK_TIMEOUT_SEC)
        return DependencyCheck(
            status=CheckStatus.UP,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except TimeoutError as e:
        log.warning("readiness.check_failed", check=name, error=str(e), exc_type=type(e).__name__)
        error, error_type = sanitize_error(e, expose_error_details=expose_error_details)
        return DependencyCheck(
            status=CheckStatus.DOWN,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            error=f"Timeout while checking {name}" if expose_error_details else "timeout",
            error_type=error_type,
        )
    except Exception as e:
        log.warning("readiness.check_failed", check=name, error=str(e), exc_type=type(e).__name__)
        error, error_type = sanitize_error(e, expose_error_details=expose_error_details)
        return DependencyCheck(
            status=CheckStatus.DOWN,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            error=error,
            error_type=error_type,
        )


async def run_readiness_checks(
    clients: AppClients,
    *,
    expose_error_details: bool
) -> ReadinessResponse:
    names_and_coros = (
        ("postgres", clients.db.ping),
        ("redis", clients.redis.ping),
        ("qdrant", clients.qdrant.ping),
    )
    results = await asyncio.gather(
        *(
            _check(name, ping, expose_error_details=expose_error_details)
            for name, ping in names_and_coros
        ),
    )
    checks = dict(zip(
        (name for name, _ in names_and_coros),
        results,
        strict=True,
    ))
    all_up = all(c.status == CheckStatus.UP for c in checks.values())
    return ReadinessResponse(
        status=CheckStatus.UP if all_up else CheckStatus.DOWN,
        checks=checks,
    )
