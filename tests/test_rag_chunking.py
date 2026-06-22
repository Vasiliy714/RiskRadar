from __future__ import annotations

from app.rag.chunking import chunk_document, split_text
from app.rag.parsers.text import parse_plain_text
from app.rag.types import ChunkType


def test_split_text_respects_markdown_headings() -> None:
    text = "## Section A\n" + ("alpha " * 200) + "\n## Section B\n" + ("beta " * 200)
    chunks = split_text(
        text,
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n\n", "\n", " ", ""],
    )
    assert len(chunks) >= 2
    assert any("alpha" in chunk for chunk in chunks)
    assert any("beta" in chunk for chunk in chunks)


def test_table_block_becomes_single_table_chunk() -> None:
    parsed = parse_plain_text("ignored")
    parsed.blocks[0].chunk_type = ChunkType.TABLE
    parsed.blocks[0].text = "1 | 2"
    parsed.blocks[0].table_data = {"header": ["a", "b"], "rows": [["1", "2"]]}

    chunks = chunk_document(parsed, chunk_size=800, chunk_overlap=150)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.TABLE
    assert chunks[0].table_data is not None
