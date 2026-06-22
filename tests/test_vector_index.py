from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from qdrant_client.http import models as qmodels

from app.core.qdrant import QdrantStore, VectorRecord
from app.llm.embeddings.mock import MockEmbeddings
from app.rag.vector_index import VectorIndexService


@pytest.fixture
def mock_qdrant_store() -> QdrantStore:
    store = QdrantStore(
        host="127.0.0.1",
        port=6333,
        grpc_port=6334,
        collection_name="test_chunks",
    )
    store.client = AsyncMock()
    store.client.get_collections.return_value = qmodels.CollectionsResponse(collections=[])
    return store


async def test_vector_index_indexes_and_searches(mock_qdrant_store: QdrantStore) -> None:
    embeddings = MockEmbeddings(vector_size=8)
    service = VectorIndexService(embeddings, mock_qdrant_store, hybrid_enabled=False)
    records = [
        VectorRecord(
            point_id="chunk-1",
            text="SBER revenue grew in 2024",
            payload={"issuer": "SBER", "doc_type": "annual_report", "is_current": True},
        )
    ]

    try:
        indexed = await service.index_records(records)
        assert indexed == 1
        mock_qdrant_store.client.create_collection.assert_awaited_once()
        mock_qdrant_store.client.upsert.assert_awaited_once()

        mock_qdrant_store.client.search = mock_qdrant_store.client.query_points
        mock_qdrant_store.client.query_points.return_value = qmodels.QueryResponse(
            points=[
                qmodels.ScoredPoint(
                    id="chunk-1",
                    version=1,
                    score=0.91,
                    payload={
                        "issuer": "SBER",
                        "doc_type": "annual_report",
                        "is_current": True,
                        "text": "SBER revenue grew in 2024",
                    },
                )
            ]
        )

        hits = await service.search(
            "revenue growth",
            issuer="SBER",
            doc_type="annual_report",
        )
        assert len(hits) == 1
        assert hits[0].point_id == "chunk-1"
        assert hits[0].score == pytest.approx(0.91)
        mock_qdrant_store.client.query_points.assert_awaited_once()
    finally:
        await embeddings.close()
