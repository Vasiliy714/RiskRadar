from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients import AppClients
from app.core.config import get_settings
from app.llm.base import LLMClient
from app.llm.embeddings.base import EmbeddingsProvider
from app.rag.ingestion import DocumentIngestionService
from app.rag.retriever import HybridRetriever
from app.rag.vector_index import VectorIndexService
from app.repositories.issuer import IssuerRepository
from app.schemas.common import PaginationParams


def get_pagination(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


def get_clients(request: Request) -> AppClients:
    return cast(AppClients, request.app.state.clients)


def get_llm(request: Request) -> LLMClient:
    return get_clients(request).llm


def get_embeddings(request: Request) -> EmbeddingsProvider:
    return get_clients(request).embeddings


def get_vector_index(request: Request) -> VectorIndexService:
    return get_clients(request).vector_index


def get_hybrid_retriever(request: Request) -> HybridRetriever:
    return get_clients(request).hybrid_retriever


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    clients = get_clients(request)
    async with clients.db.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_issuer_repository(
    session: SessionDep
) -> IssuerRepository:
    return IssuerRepository(session)


IssuerRepoDep = Annotated[IssuerRepository, Depends(get_issuer_repository)]

LLMClientDep = Annotated[LLMClient, Depends(get_llm)]
EmbeddingsDep = Annotated[EmbeddingsProvider, Depends(get_embeddings)]
VectorIndexDep = Annotated[VectorIndexService, Depends(get_vector_index)]
HybridRetrieverDep = Annotated[HybridRetriever, Depends(get_hybrid_retriever)]


def get_ingestion_service(
    session: SessionDep,
    vector_index: VectorIndexDep,
) -> DocumentIngestionService:
    settings = get_settings()
    return DocumentIngestionService(
        session=session,
        vector_index=vector_index,
        chunk_size=settings.app.rag_chunk_size,
        chunk_overlap=settings.app.rag_chunk_overlap,
    )


IngestionServiceDep = Annotated[DocumentIngestionService, Depends(get_ingestion_service)]
