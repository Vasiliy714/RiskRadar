from __future__ import annotations

import asyncio
from typing import Any

from app.llm.embeddings.base import EmbeddingsError, EmbeddingsProvider

_E5_MODELS = {
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
    "intfloat/multilingual-e5-large",
    "intfloat/e5-small-v2",
    "intfloat/e5-base-v2",
    "intfloat/e5-large-v2",
}

_KNOWN_DIMENSIONS: dict[str, int] = {
    "intfloat/multilingual-e5-small": 384,
    "intfloat/multilingual-e5-base": 768,
    "intfloat/multilingual-e5-large": 1024,
    "intfloat/e5-small-v2": 384,
    "intfloat/e5-base-v2": 768,
    "intfloat/e5-large-v2": 1024,
    "ai-forever/FRIDA": 1024,
}


def apply_e5_prefix(text: str, *, is_query: bool) -> str:
    """Добавляет E5-префиксы инструкций, если их еще нет."""
    query_prefix = "query: "
    passage_prefix = "passage: "
    if text.startswith((query_prefix, passage_prefix)):
        return text
    return f"{query_prefix if is_query else passage_prefix}{text}"


class LocalSentenceTransformerEmbeddings(EmbeddingsProvider):
    provider = "local"

    def __init__(self, model_name: str, *, batch_size: int = 32) -> None:
        self.model = model_name
        self._batch_size = batch_size
        self._model: Any = None
        self._load_lock = asyncio.Lock()
        self._uses_e5_prefix = model_name in _E5_MODELS or "e5" in model_name.lower()
        if model_name not in _KNOWN_DIMENSIONS:
            msg = f"unknown local embedding model dimension: {model_name}"
            raise EmbeddingsError(msg)
        self.vector_size = _KNOWN_DIMENSIONS[model_name]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prepared = [
            apply_e5_prefix(text, is_query=False) if self._uses_e5_prefix else text
            for text in texts
        ]
        return await self._encode_batches(prepared)

    async def embed_query(self, text: str) -> list[float]:
        prepared = apply_e5_prefix(text, is_query=True) if self._uses_e5_prefix else text
        vectors = await self._encode_batches([prepared])
        return vectors[0]

    async def close(self) -> None:
        self._model = None

    async def _encode_batches(self, texts: list[str]) -> list[list[float]]:
        model = await self._get_model()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            encoded = await asyncio.to_thread(
                model.encode,
                batch,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            vectors.extend(row.tolist() for row in encoded)
        return vectors

    async def _get_model(self) -> Any:
        async with self._load_lock:
            if self._model is None:
                self._model = await asyncio.to_thread(self._create_model)
            return self._model

    def _create_model(self) -> Any:
        try:
            import importlib

            sentence_transformers = importlib.import_module("sentence_transformers")
            sentence_transformer_cls = sentence_transformers.SentenceTransformer
        except ImportError as exc:
            msg = (
                "sentence-transformers is required for APP_EMBEDDINGS_PROVIDER=local; "
                "install it with: uv add sentence-transformers"
            )
            raise EmbeddingsError(msg) from exc

        return sentence_transformer_cls(self.model)
