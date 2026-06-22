from __future__ import annotations

import hashlib
import re
import unicodedata

_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
}

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Нормализует пробелы и Unicode-лигатуры перед хешированием или чанкингом."""
    normalized = unicodedata.normalize("NFKC", text)
    for source, target in _LIGATURES.items():
        normalized = normalized.replace(source, target)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def compute_document_key(issuer_code: str, doc_type: str, period_key: str) -> str:
    raw = f"{issuer_code}:{doc_type}:{period_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
