from __future__ import annotations

import uuid

from app.rag.normalize import compute_content_hash, normalize_text
from app.rag.types import ChunkType, ParsedBlock, ParsedDocument, TextChunk

DEFAULT_SEPARATORS: list[str] = ["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]


def chunk_document(
    parsed: ParsedDocument,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    separators: list[str] | None = None,
) -> list[TextChunk]:
    """Делит распарсенные блоки на поисковые чанки и добавляет хеши."""
    seps = separators or DEFAULT_SEPARATORS
    chunks: list[TextChunk] = []

    for block in parsed.blocks:
        if block.chunk_type == ChunkType.TABLE:
            chunks.append(_table_chunk(block))
            continue

        parent_section_id = _section_id(block.section)
        for piece in split_text(
            block.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=seps,
        ):
            chunks.append(
                TextChunk(
                    text=piece,
                    chunk_type=ChunkType.TEXT,
                    section=block.section,
                    page=block.page,
                    content_hash=compute_content_hash(piece),
                    parent_section_id=parent_section_id,
                )
            )

    return chunks


def split_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]
    return _split_recursive(normalized, separators, chunk_size, chunk_overlap)


def _split_recursive(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    separator = separators[-1]
    for candidate in separators:
        if candidate == "":
            continue
        if candidate in text:
            separator = candidate
            break

    if separator:
        parts = text.split(separator)
        chunks: list[str] = []
        current = ""
        for index, part in enumerate(parts):
            piece = part if index == len(parts) - 1 else part + separator
            if not piece:
                continue
            candidate = f"{current}{piece}".strip()
            if len(candidate) <= chunk_size:
                current = candidate if current else piece
                continue
            if current:
                chunks.extend(_split_recursive(current, separators, chunk_size, chunk_overlap))
            current = piece
        if current:
            chunks.extend(_split_recursive(current, separators, chunk_size, chunk_overlap))
    else:
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]

    return _merge_with_overlap(chunks, chunk_overlap)


def _merge_with_overlap(chunks: list[str], chunk_overlap: int) -> list[str]:
    if chunk_overlap <= 0 or len(chunks) <= 1:
        return chunks

    merged: list[str] = [chunks[0]]
    for chunk in chunks[1:]:
        previous = merged[-1]
        overlap = previous[-chunk_overlap:]
        merged.append(f"{overlap}{chunk}" if overlap else chunk)
    return merged


def _table_chunk(block: ParsedBlock) -> TextChunk:
    table_text = block.text
    if block.table_data is not None:
        header = block.table_data.get("header", [])
        rows = block.table_data.get("rows", [])
        rendered_rows = [" | ".join(str(cell) for cell in row) for row in rows]
        table_text = "\n".join([" | ".join(str(cell) for cell in header), *rendered_rows])
    return TextChunk(
        text=normalize_text(table_text),
        chunk_type=ChunkType.TABLE,
        section=block.section,
        page=block.page,
        content_hash=compute_content_hash(table_text),
        table_data=block.table_data,
        parent_section_id=_section_id(block.section),
    )


def _section_id(section: str | None) -> str | None:
    if section is None:
        return None
    return str(uuid.uuid5(uuid.NAMESPACE_URL, section))
