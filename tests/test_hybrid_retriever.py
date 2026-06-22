from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.qdrant import VectorSearchHit
from app.db.enums import DocumentType
from app.llm.embeddings.mock import MockEmbeddings
from app.rag.retriever import HybridRetriever
from app.rag.types import RetrieverType
from app.rag.vector_index import VectorIndexService


@pytest.fixture
def hybrid_retriever() -> HybridRetriever:
    qdrant = AsyncMock()
    embeddings = MockEmbeddings(vector_size=8)
    vector_index = VectorIndexService(
        embeddings,
        qdrant,
        hybrid_enabled=True,
        prefetch_limit=20,
    )
    vector_index.search = AsyncMock(
        return_value=[
            VectorSearchHit(
                point_id="chunk-1",
                score=0.9,
                payload={
                    "chunk_id": "chunk-1",
                    "document_id": "doc-1",
                    "text": "Debt ratio increased",
                    "issuer": "SBER",
                    "doc_type": "annual_report",
                    "source_url": "https://example.com",
                },
            )
        ]
    )
    return HybridRetriever(vector_index, news_decay_half_life_days=90.0)


async def test_hybrid_retriever_returns_citations(hybrid_retriever: HybridRetriever) -> None:
    results = await hybrid_retriever.retrieve(
        "debt ratio",
        issuer="SBER",
        doc_type=DocumentType.ANNUAL_REPORT,
        limit=5,
    )
    assert len(results) == 1
    assert results[0].chunk_id == "chunk-1"
    assert results[0].retriever_type == RetrieverType.HYBRID
    assert results[0].text == "Debt ratio increased"
