from collections.abc import AsyncGenerator
from typing import cast, Annotated

from fastapi import Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients import AppClients
from app.schemas.common import PaginationParams
from app.repositories.issuer import IssuerRepository
from app.llm.base import LLMClient


def get_pagination(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


def get_clients(request: Request) -> AppClients:
    return cast(AppClients, request.app.state.clients)


def get_llm(request: Request) -> LLMClient:
    return get_clients(request).llm


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
