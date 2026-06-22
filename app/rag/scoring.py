from __future__ import annotations

from datetime import UTC, datetime

from app.core.qdrant import VectorSearchHit
from app.db.enums import DocumentType


def apply_time_decay(
    hit: VectorSearchHit,
    *,
    half_life_days: float,
    now: datetime | None = None,
) -> float:
    """Понижает рейтинг устаревших новостных чанков, не меняя другие типы документов."""
    doc_type = hit.payload.get("doc_type")
    if doc_type != DocumentType.NEWS.value:
        return hit.score

    published_raw = hit.payload.get("published_at")
    if not published_raw:
        return hit.score

    published_at = _parse_datetime(published_raw)
    if published_at is None:
        return hit.score

    current = now or datetime.now(tz=UTC)
    age_days = max((current - published_at).total_seconds() / 86400.0, 0.0)
    return float(hit.score * (0.5 ** (age_days / half_life_days)))


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None
