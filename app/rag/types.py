from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ChunkType(StrEnum):
    TEXT = "text"
    TABLE = "table"


class ParsedBlock(BaseModel):
    text: str
    chunk_type: ChunkType = ChunkType.TEXT
    section: str | None = None
    page: int | None = None
    table_data: dict[str, Any] | None = None


class ParsedDocument(BaseModel):
    blocks: list[ParsedBlock]
    title: str | None = None
    language: str = "ru"


class TextChunk(BaseModel):
    text: str
    chunk_type: ChunkType = ChunkType.TEXT
    section: str | None = None
    page: int | None = None
    content_hash: str
    table_data: dict[str, Any] | None = None
    parent_section_id: str | None = None


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    issuer: str
    doc_type: str
    section: str | None = None
    page: int | None = None
    chunk_type: ChunkType = ChunkType.TEXT
    published_at: datetime | None = None
    source_url: str | None = None
    language: str = "ru"
    ingested_at: datetime
    content_hash: str
    parent_section_id: str | None = None
    is_current: bool = True
    table_data: dict[str, Any] | None = None


class IngestionStats(BaseModel):
    chunks_total: int = 0
    chunks_indexed: int = 0
    chunks_skipped_duplicate: int = 0


class RetrieverType(StrEnum):
    HYBRID = "hybrid"
    DENSE = "dense"
