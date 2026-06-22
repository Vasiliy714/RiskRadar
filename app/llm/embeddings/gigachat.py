from __future__ import annotations

import httpx

from app.core.config import GigaChatSettings
from app.llm.base import LLMPermanentError, LLMTransientError
from app.llm.embeddings.base import (
    EmbeddingsPermanentError,
    EmbeddingsProvider,
    EmbeddingsTransientError,
)
from app.llm.gigachat_oauth import GigaChatHttpSession

_GIGACHAT_EMBEDDING_DIMENSIONS: dict[str, int] = {
    "Embeddings": 1024,
    "EmbeddingsGigaR": 2560,
}


class GigaChatEmbeddings(EmbeddingsProvider):
    provider = "gigachat"

    def __init__(
        self,
        settings: GigaChatSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if settings.embeddings_model not in _GIGACHAT_EMBEDDING_DIMENSIONS:
            msg = f"unsupported GigaChat embeddings model: {settings.embeddings_model}"
            raise ValueError(msg)

        self.model = settings.embeddings_model
        self.vector_size = _GIGACHAT_EMBEDDING_DIMENSIONS[self.model]
        self._session = GigaChatHttpSession(settings, http_client=http_client)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed_batch(texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed_batch([text])
        return vectors[0]

    async def close(self) -> None:
        await self._session.close()

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, object] = {
            "model": self.model,
            "input": texts,
        }
        try:
            data, _latency_ms = await self._session.post_with_retry("/embeddings", payload)
        except LLMTransientError as exc:
            raise EmbeddingsTransientError(str(exc)) from exc
        except LLMPermanentError as exc:
            raise EmbeddingsPermanentError(str(exc)) from exc

        items = sorted(data["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items]
