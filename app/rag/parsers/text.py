from __future__ import annotations

from app.rag.normalize import normalize_text
from app.rag.types import ChunkType, ParsedBlock, ParsedDocument


def parse_plain_text(text: str, *, title: str | None = None) -> ParsedDocument:
    normalized = normalize_text(text)
    if not normalized:
        msg = "document text is empty after normalization"
        raise ValueError(msg)
    return ParsedDocument(
        title=title,
        blocks=[ParsedBlock(text=normalized, chunk_type=ChunkType.TEXT)],
    )
