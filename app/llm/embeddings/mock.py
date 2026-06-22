from __future__ import annotations

import hashlib
import math
import struct

from app.llm.embeddings.base import EmbeddingsProvider


class MockEmbeddings(EmbeddingsProvider):
    provider = "mock"
    model = "mock-embeddings"

    def __init__(self, *, vector_size: int = 384) -> None:
        self.vector_size = vector_size

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._text_to_vector(text)

    async def close(self) -> None:
        return None

    def _text_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self.vector_size:
            for chunk_start in range(0, len(digest), 4):
                if len(values) >= self.vector_size:
                    break
                chunk = digest[chunk_start : chunk_start + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b"\x00")
                raw = struct.unpack("!I", chunk)[0]
                values.append((raw / 2**32) * 2.0 - 1.0)
            digest = hashlib.sha256(digest).digest()

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return values
        return [value / norm for value in values]
