from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients import AppClients
from app.repositories.issuer import IssuerRepository
from app.schemas.common import PaginationParams


def get_clients(request: Request) -> AppClients:
    return cast(AppClients, request.app.state.clients)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    clients = get_clients(request)
    async with clients.db.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_pagination(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_issuer_repository(
    session: SessionDep
) -> IssuerRepository:
    return IssuerRepository(session)


IssuerRepoDep = Annotated[IssuerRepository, Depends(get_issuer_repository)]
