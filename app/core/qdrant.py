from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.vector_names import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME


class VectorSearchHit(BaseModel):
    point_id: str
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorRecord(BaseModel):
    point_id: str
    text: str
    payload: dict[str, Any] = Field(default_factory=dict)


class QdrantStore:
    def __init__(
        self,
        host: str,
        port: int,
        grpc_port: int,
        *,
        collection_name: str,
        prefer_grpc: bool = False,
        hybrid_enabled: bool = True,
    ) -> None:
        self.collection_name = collection_name
        self.hybrid_enabled = hybrid_enabled
        self.client = AsyncQdrantClient(
            host=host,
            port=port,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
        )

    async def ping(self) -> None:
        await self.client.get_collections()

    async def ensure_collection(self, vector_size: int) -> None:
        collections = await self.client.get_collections()
        existing = {collection.name for collection in collections.collections}
        if self.collection_name not in existing:
            if self.hybrid_enabled:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        DENSE_VECTOR_NAME: qmodels.VectorParams(
                            size=vector_size,
                            distance=qmodels.Distance.COSINE,
                        ),
                    },
                    sparse_vectors_config={
                        SPARSE_VECTOR_NAME: qmodels.SparseVectorParams(
                            index=qmodels.SparseIndexParams(on_disk=False),
                        ),
                    },
                )
            else:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
        await self._ensure_payload_indexes()

    async def upsert_records(
        self,
        records: list[VectorRecord],
        vectors: list[list[float]],
        sparse_vectors: list[qmodels.SparseVector | None] | None = None,
    ) -> None:
        if len(records) != len(vectors):
            msg = "records and vectors length mismatch"
            raise ValueError(msg)

        points: list[qmodels.PointStruct] = []
        for index, (record, vector) in enumerate(zip(records, vectors, strict=True)):
            if self.hybrid_enabled:
                named_vector: dict[str, list[float] | qmodels.SparseVector] = {
                    DENSE_VECTOR_NAME: vector,
                }
                if sparse_vectors is not None:
                    sparse = sparse_vectors[index]
                    if sparse is not None:
                        named_vector[SPARSE_VECTOR_NAME] = sparse
                point_vector: list[float] | dict[str, list[float] | qmodels.SparseVector] = (
                    named_vector
                )
            else:
                point_vector = vector

            points.append(
                qmodels.PointStruct(
                    id=record.point_id,
                    vector=point_vector,
                    payload={**record.payload, "text": record.text},
                )
            )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        payload_filter: qmodels.Filter | None = None,
    ) -> list[VectorSearchHit]:
        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using=DENSE_VECTOR_NAME if self.hybrid_enabled else None,
            query_filter=payload_filter,
            limit=limit,
            with_payload=True,
        )
        return _hits_from_response(results)

    async def hybrid_search(
        self,
        dense_vector: list[float],
        sparse_vector: qmodels.SparseVector,
        *,
        limit: int = 10,
        prefetch_limit: int = 50,
        payload_filter: qmodels.Filter | None = None,
    ) -> list[VectorSearchHit]:
        results = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                qmodels.Prefetch(
                    query=dense_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=prefetch_limit,
                    filter=payload_filter,
                ),
                qmodels.Prefetch(
                    query=sparse_vector,
                    using=SPARSE_VECTOR_NAME,
                    limit=prefetch_limit,
                    filter=payload_filter,
                ),
            ],
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            query_filter=payload_filter,
            limit=limit,
            with_payload=True,
        )
        return _hits_from_response(results)

    async def close(self) -> None:
        await self.client.close()

    async def content_hash_exists(self, content_hash: str) -> bool:
        points, _next = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="content_hash",
                        match=qmodels.MatchValue(value=content_hash),
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        return len(points) > 0

    async def mark_document_stale(self, document_id: str) -> None:
        await self.client.set_payload(
            collection_name=self.collection_name,
            payload={"is_current": False},
            points=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            ),
            wait=True,
        )

    async def _ensure_payload_indexes(self) -> None:
        index_specs: list[tuple[str, qmodels.PayloadSchemaType]] = [
            ("issuer", qmodels.PayloadSchemaType.KEYWORD),
            ("doc_type", qmodels.PayloadSchemaType.KEYWORD),
            ("is_current", qmodels.PayloadSchemaType.BOOL),
            ("document_id", qmodels.PayloadSchemaType.KEYWORD),
            ("content_hash", qmodels.PayloadSchemaType.KEYWORD),
            ("published_at", qmodels.PayloadSchemaType.DATETIME),
        ]
        for field_name, field_schema in index_specs:
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception:
                continue


def _hits_from_response(results: qmodels.QueryResponse) -> list[VectorSearchHit]:
    return [
        VectorSearchHit(
            point_id=str(point.id),
            score=point.score,
            payload=point.payload or {},
        )
        for point in results.points
    ]
