from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DocumentType, IngestionJobStatus
from app.db.models.document import Document
from app.db.models.ingestion_job import IngestionJob


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def get_by_content_hash(self, content_hash: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.content_hash == content_hash),
        )
        return result.scalar_one_or_none()

    async def find_current_by_period(
        self,
        *,
        issuer_id: uuid.UUID,
        doc_type: DocumentType,
        period_key: str,
    ) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.issuer_id == issuer_id,
                Document.doc_type == doc_type,
                Document.is_current.is_(True),
                Document.metadata_.contains({"period_key": period_key}),
            )
        )
        return result.scalar_one_or_none()

    async def supersede_current(
        self,
        *,
        issuer_id: uuid.UUID,
        doc_type: DocumentType,
        period_key: str,
    ) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(Document.id).where(
                Document.issuer_id == issuer_id,
                Document.doc_type == doc_type,
                Document.is_current.is_(True),
                Document.metadata_.contains({"period_key": period_key}),
            )
        )
        document_ids = list(result.scalars().all())
        if not document_ids:
            return []

        await self._session.execute(
            update(Document)
            .where(Document.id.in_(document_ids))
            .values(is_current=False, updated_at=datetime.now(tz=UTC)),
        )
        await self._session.flush()
        return document_ids

    async def create(
        self,
        *,
        issuer_id: uuid.UUID,
        doc_type: DocumentType,
        title: str,
        content_hash: str,
        source_url: str | None,
        published_at: datetime | None,
        metadata: dict[str, Any],
    ) -> Document:
        document = Document(
            issuer_id=issuer_id,
            doc_type=doc_type,
            title=title,
            source_url=source_url,
            published_at=published_at,
            content_hash=content_hash,
            metadata_=metadata,
            is_current=True,
        )
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document


class IngestionJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, document_id: uuid.UUID, payload: dict[str, Any]) -> IngestionJob:
        job = IngestionJob(
            document_id=document_id,
            status=IngestionJobStatus.QUEUED,
            payload=payload,
        )
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_running(self, job: IngestionJob) -> IngestionJob:
        job.status = IngestionJobStatus.RUNNING
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_succeeded(
        self,
        job: IngestionJob,
        *,
        stats: dict[str, Any],
    ) -> IngestionJob:
        job.status = IngestionJobStatus.SUCCEEDED
        job.payload = {**job.payload, **stats}
        job.error_message = None
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_failed(self, job: IngestionJob, *, error_message: str) -> IngestionJob:
        job.status = IngestionJobStatus.FAILED
        job.error_message = error_message
        await self._session.flush()
        await self._session.refresh(job)
        return job
