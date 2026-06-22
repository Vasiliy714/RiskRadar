from __future__ import annotations

import time

from app.core.qdrant import VectorSearchHit
from app.db.enums import DocumentType
from app.observability.metrics import RAG_SEARCH_DURATION_SECONDS, RAG_SEARCH_REQUESTS_TOTAL
from app.rag.scoring import apply_time_decay
from app.rag.types import RetrieverType
from app.rag.vector_index import VectorIndexService
from app.schemas.retrieval import Citation


class HybridRetriever:
    """Гибридный поиск по плотным и разреженным векторам учитывает давность новостей."""

    def __init__(
        self,
        vector_index: VectorIndexService,
        *,
        news_decay_half_life_days: float = 90.0,
    ) -> None:
        self._vector_index = vector_index
        self._news_decay_half_life_days = news_decay_half_life_days

    async def retrieve(
        self,
        query: str,
        *,
        issuer: str,
        doc_type: DocumentType | None = None,
        limit: int = 10,
    ) -> list[Citation]:
        start = time.perf_counter()
        retriever_type = (
            RetrieverType.HYBRID
            if self._vector_index.hybrid_enabled
            else RetrieverType.DENSE
        )

        try:
            hits = await self._vector_index.search(
                query,
                limit=limit,
                issuer=issuer,
                doc_type=doc_type.value if doc_type is not None else None,
            )
        except Exception:
            RAG_SEARCH_REQUESTS_TOTAL.labels(outcome="error").inc()
            RAG_SEARCH_DURATION_SECONDS.observe(time.perf_counter() - start)
            raise

        ranked = sorted(
            (
                apply_time_decay(
                    hit,
                    half_life_days=self._news_decay_half_life_days,
                ),
                hit,
            )
            for hit in hits
        )
        ranked.sort(key=lambda item: item[0], reverse=True)

        citations = [
            _to_citation(hit, score=score, retriever_type=retriever_type)
            for score, hit in ranked[:limit]
        ]

        RAG_SEARCH_REQUESTS_TOTAL.labels(outcome="success").inc()
        RAG_SEARCH_DURATION_SECONDS.observe(time.perf_counter() - start)
        return citations


def _to_citation(
    hit: VectorSearchHit,
    *,
    score: float,
    retriever_type: RetrieverType,
) -> Citation:
    payload = hit.payload
    return Citation(
        chunk_id=str(payload.get("chunk_id", hit.point_id)),
        document_id=str(payload.get("document_id", "")),
        score=score,
        text=str(payload.get("text", "")),
        issuer=str(payload.get("issuer", "")),
        doc_type=str(payload.get("doc_type", "")),
        source_url=payload.get("source_url"),
        page=payload.get("page"),
        section=payload.get("section"),
        retriever_type=retriever_type,
    )
