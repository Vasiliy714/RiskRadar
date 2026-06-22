from __future__ import annotations

import importlib
from typing import Any

from app.rag.normalize import normalize_text
from app.rag.types import ChunkType, ParsedBlock, ParsedDocument


def parse_pdf(data: bytes, *, title: str | None = None) -> ParsedDocument:
    """Разбирает текстовые блоки и таблицы PDF через PyMuPDF + pdfplumber."""
    try:
        fitz = importlib.import_module("fitz")
        pdfplumber = importlib.import_module("pdfplumber")
    except ImportError as exc:
        msg = "pymupdf and pdfplumber are required for PDF ingestion"
        raise ValueError(msg) from exc

    blocks: list[ParsedBlock] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page_index, page in enumerate(doc, start=1):
            page_text = normalize_text(page.get_text("text"))
            if page_text:
                blocks.append(
                    ParsedBlock(
                        text=page_text,
                        chunk_type=ChunkType.TEXT,
                        page=page_index,
                    )
                )

    with pdfplumber.open(data) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for table_index, table in enumerate(tables, start=1):
                table_data = _table_to_payload(table)
                if table_data is None:
                    continue
                blocks.append(
                    ParsedBlock(
                        text=table_data["text"],
                        chunk_type=ChunkType.TABLE,
                        page=page_index,
                        section=f"table_{page_index}_{table_index}",
                        table_data={"header": table_data["header"], "rows": table_data["rows"]},
                    )
                )

    if not blocks:
        msg = "pdf document contains no extractable text or tables"
        raise ValueError(msg)

    return ParsedDocument(title=title, blocks=blocks)


def _table_to_payload(table: list[list[Any | None]]) -> dict[str, Any] | None:
    if not table:
        return None
    header = [str(cell or "").strip() for cell in table[0]]
    rows = [[str(cell or "").strip() for cell in row] for row in table[1:]]
    rows = [row for row in rows if any(cell for cell in row)]
    if not any(header) and not rows:
        return None
    text = "\n".join([" | ".join(header), *(" | ".join(row) for row in rows)])
    return {"header": header, "rows": rows, "text": normalize_text(text)}
