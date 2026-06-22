from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import DocumentType, IngestionJobStatus


class IngestDocumentRequest(BaseModel):
    issuer_code: str = Field(min_length=1, max_length=32)
    doc_type: DocumentType
    title: str = Field(min_length=1, max_length=512)
    period_key: str = Field(min_length=1, max_length=64, examples=["2024", "2024-Q1"])
    text: str = Field(min_length=1)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: datetime | None = None


class IngestDocumentResponse(BaseModel):
    document_id: uuid.UUID
    ingestion_job_id: uuid.UUID
    status: IngestionJobStatus
    chunks_total: int
    chunks_indexed: int
    chunks_skipped_duplicate: int
    idempotent: bool = False
