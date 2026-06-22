from __future__ import annotations

from pydantic import BaseModel, Field

from app.rag.types import RetrieverType


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    score: float = Field(ge=0.0)
    text: str
    issuer: str
    doc_type: str
    source_url: str | None = None
    page: int | None = None
    section: str | None = None
    retriever_type: RetrieverType


class SearchResponse(BaseModel):
    query: str
    issuer_code: str
    results: list[Citation]
