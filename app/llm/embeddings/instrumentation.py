import time

from app.llm.embeddings.base import (
    EmbeddingsPermanentError,
    EmbeddingsProvider,
    EmbeddingsTransientError,
)
from app.observability.metrics import (
    EMBEDDINGS_DURATION_SECONDS,
    EMBEDDINGS_REQUESTS_TOTAL,
    EMBEDDINGS_VECTORS_TOTAL,
)


class InstrumentedEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, inner: EmbeddingsProvider) -> None:
        self._inner = inner
        self.provider = inner.provider
        self.model = inner.model
        self.vector_size = inner.vector_size

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        start = time.perf_counter()
        try:
            vectors = await self._inner.embed_documents(texts)
        except EmbeddingsPermanentError:
            elapsed = time.perf_counter() - start
            EMBEDDINGS_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=self.model,
                kind="document",
                outcome="permanent_error",
            ).inc()
            EMBEDDINGS_DURATION_SECONDS.labels(
                provider=self.provider,
                model=self.model,
                kind="document",
            ).observe(elapsed)
            raise
        except EmbeddingsTransientError:
            elapsed = time.perf_counter() - start
            EMBEDDINGS_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=self.model,
                kind="document",
                outcome="transient_error",
            ).inc()
            EMBEDDINGS_DURATION_SECONDS.labels(
                provider=self.provider,
                model=self.model,
                kind="document",
            ).observe(elapsed)
            raise

        elapsed = time.perf_counter() - start
        EMBEDDINGS_REQUESTS_TOTAL.labels(
            provider=self.provider,
            model=self.model,
            kind="document",
            outcome="success",
        ).inc()
        EMBEDDINGS_DURATION_SECONDS.labels(
            provider=self.provider,
            model=self.model,
            kind="document",
        ).observe(elapsed)
        EMBEDDINGS_VECTORS_TOTAL.labels(
            provider=self.provider,
            model=self.model,
            kind="document",
        ).inc(len(texts))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        start = time.perf_counter()
        try:
            vector = await self._inner.embed_query(text)
        except EmbeddingsPermanentError:
            elapsed = time.perf_counter() - start
            EMBEDDINGS_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=self.model,
                kind="query",
                outcome="permanent_error",
            ).inc()
            EMBEDDINGS_DURATION_SECONDS.labels(
                provider=self.provider,
                model=self.model,
                kind="query",
            ).observe(elapsed)
            raise
        except EmbeddingsTransientError:
            elapsed = time.perf_counter() - start
            EMBEDDINGS_REQUESTS_TOTAL.labels(
                provider=self.provider,
                model=self.model,
                kind="query",
                outcome="transient_error",
            ).inc()
            EMBEDDINGS_DURATION_SECONDS.labels(
                provider=self.provider,
                model=self.model,
                kind="query",
            ).observe(elapsed)
            raise

        elapsed = time.perf_counter() - start
        EMBEDDINGS_REQUESTS_TOTAL.labels(
            provider=self.provider,
            model=self.model,
            kind="query",
            outcome="success",
        ).inc()
        EMBEDDINGS_DURATION_SECONDS.labels(
            provider=self.provider,
            model=self.model,
            kind="query",
        ).observe(elapsed)
        EMBEDDINGS_VECTORS_TOTAL.labels(
            provider=self.provider,
            model=self.model,
            kind="query",
        ).inc()
        return vector

    async def close(self) -> None:
        await self._inner.close()
