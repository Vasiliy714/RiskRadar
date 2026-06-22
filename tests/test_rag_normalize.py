from __future__ import annotations

from app.rag.normalize import compute_content_hash, normalize_text


def test_normalize_text_collapses_whitespace_and_ligatures() -> None:
    raw = "  Revenue\uFB01ts   grew\n\nin 2024  "
    assert normalize_text(raw) == "Revenuefits grew in 2024"


def test_compute_content_hash_is_stable() -> None:
    first = compute_content_hash("Same text")
    second = compute_content_hash("Same text")
    different = compute_content_hash("Different text")
    assert first == second
    assert first != different
    assert len(first) == 64
