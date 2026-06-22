from __future__ import annotations

import re
import zlib
from collections import Counter

from qdrant_client.http import models as qmodels

from app.rag.normalize import normalize_text

DEFAULT_SPARSE_DIM = 2**18

_TOKEN_RE = re.compile(r"[\w\d]+", re.UNICODE)


class HashSparseEncoder:
    """BM25-подобные разреженные векторы для гибридного поиска без ML-зависимостей."""

    def __init__(self, *, dim: int = DEFAULT_SPARSE_DIM) -> None:
        self._dim = dim

    def encode(self, text: str) -> qmodels.SparseVector:
        normalized = normalize_text(text).lower()
        tokens = _TOKEN_RE.findall(normalized)
        if not tokens:
            return qmodels.SparseVector(indices=[], values=[])

        counts = Counter(tokens)
        indices: list[int] = []
        values: list[float] = []
        for token, count in counts.items():
            indices.append(_token_index(token, self._dim))
            values.append(float(count))
        return qmodels.SparseVector(indices=indices, values=values)

    def encode_query(self, query: str) -> qmodels.SparseVector:
        return self.encode(query)


def _token_index(token: str, dim: int) -> int:
    return zlib.crc32(token.encode("utf-8")) % dim
