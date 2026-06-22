from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.qdrant import VectorRecord
from app.db.enums import DocumentType
from app.db.models.document import Document
from app.db.models.ingestion_job import IngestionJob
from app.db.models.issuer import Issuer
from app.observability.metrics import RAG_CHUNKS_INDEXED_TOTAL, RAG_CHUNKS_SKIPPED_TOTAL
from app.rag.chunking import chunk_document
from app.rag.normalize import compute_content_hash, compute_document_key
from app.rag.parsers import SourceFormat, parse_source
from app.rag.types import ChunkMetadata, IngestionStats, TextChunk
from app.rag.vector_index import VectorIndexService
from app.repositories.document import DocumentRepository, IngestionJobRepository

log = get_logger(__name__)


class DocumentIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        vector_index: VectorIndexService,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ) -> None:
        self._session = session
        self._vector_index = vector_index
        self._documents = DocumentRepository(session)
        self._jobs = IngestionJobRepository(session)
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest_text(
        self,
        *,
        issuer: Issuer,
        doc_type: DocumentType,
        title: str,
        text: str,
        period_key: str,
        source_url: str | None = None,
        published_at: datetime | None = None,
        source_format: SourceFormat = SourceFormat.TEXT,
        raw_content: str | bytes | None = None,
    ) -> tuple[Document, IngestionJob, IngestionStats]:
        content = raw_content if raw_content is not None else text
        parsed = parse_source(content=content, source_format=source_format, title=title)
        full_text = "\n\n".join(block.text for block in parsed.blocks)
        document_hash = compute_content_hash(full_text)

        existing = await self._documents.get_by_content_hash(document_hash)
        if existing is not None:
            stats = IngestionStats()
            job = await self._jobs.create(
                document_id=existing.id,
                payload={"idempotent": True, **stats.model_dump()},
            )
            await self._jobs.mark_succeeded(job, stats=stats.model_dump())
            return existing, job, stats

        superseded_ids = await self._documents.supersede_current(
            issuer_id=issuer.id,
            doc_type=doc_type,
            period_key=period_key,
        )
        for old_document_id in superseded_ids:
            await self._vector_index.mark_document_stale(str(old_document_id))

        document = await self._documents.create(
            issuer_id=issuer.id,
            doc_type=doc_type,
            title=title,
            content_hash=document_hash,
            source_url=source_url,
            published_at=published_at,
            metadata={
                "period_key": period_key,
                "document_key": compute_document_key(issuer.code, doc_type.value, period_key),
                "language": parsed.language,
            },
        )

        job = await self._jobs.create(
            document_id=document.id,
            payload={"period_key": period_key, "source_format": source_format.value},
        )
        await self._jobs.mark_running(job)

        try:
            chunks = chunk_document(
                parsed,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
            stats = await self._index_chunks(
                document=document,
                issuer_code=issuer.code,
                chunks=chunks,
                source_url=source_url,
                published_at=published_at,
                language=parsed.language,
            )
            await self._jobs.mark_succeeded(job, stats=stats.model_dump())
            log.info(
                "rag.ingestion.succeeded",
                document_id=str(document.id),
                chunks_indexed=stats.chunks_indexed,
                chunks_skipped=stats.chunks_skipped_duplicate,
            )
            return document, job, stats
        except Exception as exc:
            await self._jobs.mark_failed(job, error_message=str(exc) or type(exc).__name__)
            raise

    async def _index_chunks(
        self,
        *,
        document: Document,
        issuer_code: str,
        chunks: list[TextChunk],
        source_url: str | None,
        published_at: datetime | None,
        language: str,
    ) -> IngestionStats:
        ingested_at = datetime.now(tz=UTC)
        records: list[VectorRecord] = []
        skipped = 0

        for index, chunk in enumerate(chunks):
            if await self._vector_index.content_hash_exists(chunk.content_hash):
                skipped += 1
                RAG_CHUNKS_SKIPPED_TOTAL.labels(reason="duplicate").inc()
                continue

            chunk_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{document.id}:{index}:{chunk.content_hash}",
                )
            )
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=str(document.id),
                issuer=issuer_code,
                doc_type=document.doc_type.value,
                section=chunk.section,
                page=chunk.page,
                chunk_type=chunk.chunk_type,
                published_at=published_at,
                source_url=source_url,
                language=language,
                ingested_at=ingested_at,
                content_hash=chunk.content_hash,
                parent_section_id=chunk.parent_section_id,
                is_current=True,
                table_data=chunk.table_data,
            )
            records.append(
                VectorRecord(
                    point_id=chunk_id,
                    text=chunk.text,
                    payload=metadata.model_dump(mode="json"),
                )
            )

        indexed = await self._vector_index.index_records(records)
        RAG_CHUNKS_INDEXED_TOTAL.inc(indexed)
        return IngestionStats(
            chunks_total=len(chunks),
            chunks_indexed=indexed,
            chunks_skipped_duplicate=skipped,
        )
