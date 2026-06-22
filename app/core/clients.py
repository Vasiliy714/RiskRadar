from dataclasses import dataclass

from app.core.config import Settings
from app.core.db import DatabaseClient
from app.core.logging import get_logger
from app.core.qdrant import QdrantStore
from app.core.redis import RedisClient
from app.llm.base import LLMClient
from app.llm.circuit_breaker import CircuitBreakerLLMClient
from app.llm.deepseek import DeepSeekClient
from app.llm.embeddings.base import EmbeddingsProvider
from app.llm.embeddings.gigachat import GigaChatEmbeddings
from app.llm.embeddings.instrumentation import InstrumentedEmbeddingsProvider
from app.llm.embeddings.local import LocalSentenceTransformerEmbeddings
from app.llm.embeddings.mock import MockEmbeddings
from app.llm.gigachat import GigaChatClient
from app.llm.instrumentation import InstrumentedLLMClient
from app.llm.mock import MockLLMClient
from app.llm.router import LLMRouter
from app.rag.retriever import HybridRetriever
from app.rag.vector_index import VectorIndexService

log = get_logger(__name__)

_DEFAULT_LOCAL_EMBEDDINGS_MODEL = "intfloat/multilingual-e5-small"


@dataclass(slots=True)
class AppClients:
    db: DatabaseClient
    redis: RedisClient
    qdrant: QdrantStore
    llm: LLMClient
    embeddings: EmbeddingsProvider
    vector_index: VectorIndexService
    hybrid_retriever: HybridRetriever


def create_clients(settings: Settings, *, db_echo: bool = False) -> AppClients:
    qdrant = QdrantStore(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        grpc_port=settings.qdrant.grpc_port,
        collection_name=settings.qdrant.collection_name,
        hybrid_enabled=settings.app.rag_hybrid_enabled,
    )
    embeddings = _create_embeddings(settings)
    vector_index = VectorIndexService(
        embeddings,
        qdrant,
        hybrid_enabled=settings.app.rag_hybrid_enabled,
        prefetch_limit=settings.app.rag_search_prefetch_limit,
    )
    hybrid_retriever = HybridRetriever(
        vector_index,
        news_decay_half_life_days=settings.app.rag_news_decay_half_life_days,
    )
    return AppClients(
        db=DatabaseClient(settings.postgres.url, echo=db_echo),
        redis=RedisClient(settings.redis.url),
        qdrant=qdrant,
        llm=_create_llm(settings),
        embeddings=embeddings,
        vector_index=vector_index,
        hybrid_retriever=hybrid_retriever,
    )


def _create_embeddings(settings: Settings) -> EmbeddingsProvider:
    match settings.app.embeddings_provider:
        case "mock":
            provider: EmbeddingsProvider = MockEmbeddings()
        case "local":
            model_name = settings.app.embeddings_model or _DEFAULT_LOCAL_EMBEDDINGS_MODEL
            provider = LocalSentenceTransformerEmbeddings(
                model_name,
                batch_size=settings.app.embeddings_batch_size,
            )
        case "gigachat":
            provider = GigaChatEmbeddings(settings.gigachat)
        case _:
            msg = f"Unknown embeddings provider: {settings.app.embeddings_provider!r}"
            raise ValueError(msg)
    return InstrumentedEmbeddingsProvider(provider)


def _wrap_provider(client: LLMClient, settings: Settings) -> LLMClient:
    cb = CircuitBreakerLLMClient(
        client,
        failure_threshold=settings.app.llm_cb_failure_threshold,
        cooldown_seconds=settings.app.llm_cb_cooldown_seconds,
    )
    return InstrumentedLLMClient(cb)


def _build_gigachat(settings: Settings) -> GigaChatClient:
    if settings.gigachat.auth_key is None:
        msg = "GIGACHAT_AUTH_KEY is required for GigaChat"
        raise ValueError(msg)
    return GigaChatClient(settings.gigachat)


def _build_deepseek(settings: Settings) -> DeepSeekClient:
    if settings.deepseek.api_key is None:
        msg = "DEEPSEEK_API_KEY is required for DeepSeek"
        raise ValueError(msg)
    return DeepSeekClient(settings.deepseek)


def _create_llm(settings: Settings) -> LLMClient:
    match settings.app.llm_provider:
        case "mock":
            return InstrumentedLLMClient(MockLLMClient())
        case "gigachat":
            return _wrap_provider(_build_gigachat(settings), settings)
        case "deepseek":
            return _wrap_provider(_build_deepseek(settings), settings)
        case "router":
            primary = _wrap_provider(_build_gigachat(settings), settings)
            fallbacks: list[LLMClient] = []
            if settings.deepseek.api_key is not None:
                fallbacks.append(_wrap_provider(_build_deepseek(settings), settings))
            return LLMRouter(primary, fallbacks)
        case _:
            msg = f"Unknown LLM provider: {settings.app.llm_provider!r}"
            raise ValueError(msg)


async def shutdown_clients(clients: AppClients) -> None:
    for name, client in (
        ("llm", clients.llm),
        ("embeddings", clients.embeddings),
        ("qdrant", clients.qdrant),
        ("redis", clients.redis),
        ("db", clients.db),
    ):
        try:
            await client.close()
        except Exception as exc:
            log.error("infra.close_failed", client=name, error=str(exc) or type(exc).__name__)
