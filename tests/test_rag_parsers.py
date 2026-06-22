from __future__ import annotations

from app.rag.parsers.html import parse_html
from app.rag.parsers.text import parse_plain_text


def test_parse_plain_text_returns_single_block() -> None:
    parsed = parse_plain_text("Issuer revenue increased.", title="Report")
    assert parsed.title == "Report"
    assert len(parsed.blocks) == 1
    assert "Issuer revenue increased." in parsed.blocks[0].text


def test_parse_html_strips_tags() -> None:
    parsed = parse_html("<html><body><h1>Title</h1><p>Debt ratio is high.</p></body></html>")
    assert "Debt ratio is high." in parsed.blocks[0].text
    assert "<p>" not in parsed.blocks[0].text
