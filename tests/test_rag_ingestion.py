from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.enums import DocumentType, IngestionJobStatus
from app.db.models.document import Document
from app.db.models.ingestion_job import IngestionJob
from app.db.models.issuer import Issuer
from app.rag.ingestion import DocumentIngestionService


@pytest.fixture
def issuer() -> Issuer:
    return Issuer(
        id=uuid.uuid4(),
        code="SBER",
        name="Sberbank",
        is_public=True,
    )


@pytest.fixture
def ingestion_service() -> DocumentIngestionService:
    session = MagicMock()
    vector_index = AsyncMock()
    vector_index.content_hash_exists.return_value = False
    vector_index.index_records.return_value = 1

    service = DocumentIngestionService(session, vector_index, chunk_size=800, chunk_overlap=150)
    service._documents = AsyncMock()
    service._jobs = AsyncMock()
    return service


async def test_ingest_text_indexes_chunks(
    ingestion_service: DocumentIngestionService,
    issuer: Issuer,
) -> None:
    document = Document(
        id=uuid.uuid4(),
        issuer_id=issuer.id,
        doc_type=DocumentType.ANNUAL_REPORT,
        title="Annual report",
        content_hash="abc",
        is_current=True,
    )
    job = IngestionJob(
        id=uuid.uuid4(),
        document_id=document.id,
        status=IngestionJobStatus.RUNNING,
        payload={},
    )

    ingestion_service._documents.get_by_content_hash.return_value = None
    ingestion_service._documents.supersede_current.return_value = []
    ingestion_service._documents.create.return_value = document
    ingestion_service._jobs.create.return_value = job
    ingestion_service._jobs.mark_running.return_value = job
    ingestion_service._jobs.mark_succeeded.return_value = job

    long_text = "## Financials\n" + ("Revenue increased. " * 120)
    _, returned_job, stats = await ingestion_service.ingest_text(
        issuer=issuer,
        doc_type=DocumentType.ANNUAL_REPORT,
        title="Annual report",
        text=long_text,
        period_key="2024",
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert returned_job is job
    assert stats.chunks_total >= 1
    assert stats.chunks_indexed >= 1
    ingestion_service._vector_index.index_records.assert_awaited()


async def test_ingest_text_is_idempotent_for_same_content(
    ingestion_service: DocumentIngestionService,
    issuer: Issuer,
) -> None:
    existing = Document(
        id=uuid.uuid4(),
        issuer_id=issuer.id,
        doc_type=DocumentType.NEWS,
        title="News",
        content_hash="same-hash",
        is_current=True,
    )
    job = IngestionJob(
        id=uuid.uuid4(),
        document_id=existing.id,
        status=IngestionJobStatus.SUCCEEDED,
        payload={"idempotent": True},
    )

    ingestion_service._documents.get_by_content_hash.return_value = existing
    ingestion_service._jobs.create.return_value = job
    ingestion_service._jobs.mark_succeeded.return_value = job

    document, _, stats = await ingestion_service.ingest_text(
        issuer=issuer,
        doc_type=DocumentType.NEWS,
        title="News",
        text="Same news text for duplicate ingestion.",
        period_key="2024-05-24",
    )

    assert document.id == existing.id
    assert stats.chunks_indexed == 0
    ingestion_service._vector_index.index_records.assert_not_awaited()
