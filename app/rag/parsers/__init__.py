from __future__ import annotations

from enum import StrEnum

from app.rag.parsers.html import parse_html
from app.rag.parsers.pdf import parse_pdf
from app.rag.parsers.text import parse_plain_text
from app.rag.types import ParsedDocument


class SourceFormat(StrEnum):
    TEXT = "text"
    HTML = "html"
    PDF = "pdf"


def parse_source(
    *,
    content: str | bytes,
    source_format: SourceFormat,
    title: str | None = None,
) -> ParsedDocument:
    match source_format:
        case SourceFormat.TEXT:
            if not isinstance(content, str):
                msg = "text format requires string content"
                raise TypeError(msg)
            return parse_plain_text(content, title=title)
        case SourceFormat.HTML:
            if not isinstance(content, str):
                msg = "html format requires string content"
                raise TypeError(msg)
            return parse_html(content, title=title)
        case SourceFormat.PDF:
            if not isinstance(content, (bytes, bytearray)):
                msg = "pdf format requires bytes content"
                raise TypeError(msg)
            return parse_pdf(bytes(content), title=title)
        case _:
            msg = f"unsupported source format: {source_format!r}"
            raise ValueError(msg)


def detect_source_format(
    *,
    filename: str | None,
    content_type: str | None,
) -> SourceFormat:
    lowered_name = (filename or "").lower()
    lowered_type = (content_type or "").lower()

    if lowered_name.endswith(".pdf") or lowered_type == "application/pdf":
        return SourceFormat.PDF
    if lowered_name.endswith((".html", ".htm")) or lowered_type in {
        "text/html",
        "application/xhtml+xml",
    }:
        return SourceFormat.HTML
    return SourceFormat.TEXT


__all__ = [
    "SourceFormat",
    "detect_source_format",
    "parse_html",
    "parse_pdf",
    "parse_plain_text",
    "parse_source",
]
