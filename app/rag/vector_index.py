from __future__ import annotations

from qdrant_client.http import models as qmodels

from app.core.qdrant import QdrantStore, VectorRecord, VectorSearchHit
from app.llm.embeddings.base import EmbeddingsProvider
from app.rag.filters import build_payload_filter
from app.rag.sparse import HashSparseEncoder


class VectorIndexService:
    """Связывает провайдер эмбеддингов и Qdrant для индексации и поиска."""

    def __init__(
        self,
        embeddings: EmbeddingsProvider,
        qdrant: QdrantStore,
        *,
        sparse_encoder: HashSparseEncoder | None = None,
        hybrid_enabled: bool | None = None,
        prefetch_limit: int = 50,
    ) -> None:
        self._embeddings = embeddings
        self._qdrant = qdrant
        self._sparse_encoder = sparse_encoder or HashSparseEncoder()
        self.hybrid_enabled = (
            hybrid_enabled if hybrid_enabled is not None else qdrant.hybrid_enabled
        )
        self._prefetch_limit = prefetch_limit

    @property
    def vector_size(self) -> int:
        return self._embeddings.vector_size

    async def index_records(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0

        texts = [record.text for record in records]
        vectors = await self._embeddings.embed_documents(texts)
        sparse_vectors: list[qmodels.SparseVector | None] | None = None
        if self.hybrid_enabled:
            sparse_vectors = [self._sparse_encoder.encode(text) for text in texts]

        await self._qdrant.ensure_collection(self._embeddings.vector_size)
        await self._qdrant.upsert_records(records, vectors, sparse_vectors)
        return len(records)

    async def content_hash_exists(self, content_hash: str) -> bool:
        return await self._qdrant.content_hash_exists(content_hash)

    async def mark_document_stale(self, document_id: str) -> None:
        await self._qdrant.mark_document_stale(document_id)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        issuer: str | None = None,
        doc_type: str | None = None,
        is_current: bool | None = True,
    ) -> list[VectorSearchHit]:
        payload_filter = build_payload_filter(
            issuer=issuer,
            doc_type=doc_type,
            is_current=is_current,
        )

        if self.hybrid_enabled:
            dense_vector = await self._embeddings.embed_query(query)
            sparse_vector = self._sparse_encoder.encode_query(query)
            return await self._qdrant.hybrid_search(
                dense_vector,
                sparse_vector,
                limit=limit,
                prefetch_limit=self._prefetch_limit,
                payload_filter=payload_filter,
            )

        query_vector = await self._embeddings.embed_query(query)
        return await self._qdrant.search(
            query_vector,
            limit=limit,
            payload_filter=payload_filter,
        )
