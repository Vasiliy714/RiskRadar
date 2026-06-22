from __future__ import annotations

from datetime import UTC, datetime

from app.core.qdrant import VectorSearchHit
from app.rag.scoring import apply_time_decay
from app.rag.sparse import HashSparseEncoder


def test_hash_sparse_encoder_produces_indices_and_values() -> None:
    encoder = HashSparseEncoder(dim=1024)
    vector = encoder.encode("SBER debt ratio increased in 2024")
    assert vector.indices
    assert vector.values
    assert len(vector.indices) == len(vector.values)


def test_time_decay_reduces_old_news_score() -> None:
    hit = VectorSearchHit(
        point_id="chunk-1",
        score=1.0,
        payload={
            "doc_type": "news",
            "published_at": "2024-01-01T00:00:00+00:00",
        },
    )
    adjusted = apply_time_decay(
        hit,
        half_life_days=90.0,
        now=datetime(2024, 7, 1, tzinfo=UTC),
    )
    assert adjusted < hit.score


def test_time_decay_ignores_non_news_documents() -> None:
    hit = VectorSearchHit(
        point_id="chunk-1",
        score=0.8,
        payload={
            "doc_type": "annual_report",
            "published_at": "2020-01-01T00:00:00+00:00",
        },
    )
    assert apply_time_decay(hit, half_life_days=90.0) == hit.score
