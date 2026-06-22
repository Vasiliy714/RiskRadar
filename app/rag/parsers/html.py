from __future__ import annotations

from html.parser import HTMLParser

from app.rag.normalize import normalize_text
from app.rag.types import ParsedBlock, ParsedDocument


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = normalize_text(data)
        if cleaned:
            self._parts.append(cleaned)

    def get_text(self) -> str:
        return normalize_text(" ".join(self._parts))


def parse_html(html: str, *, title: str | None = None) -> ParsedDocument:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    text = parser.get_text()
    if not text:
        msg = "html document contains no extractable text"
        raise ValueError(msg)
    return ParsedDocument(
        title=title,
        blocks=[ParsedBlock(text=text)],
    )
