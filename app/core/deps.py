from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients import AppClients


def get_clients(request: Request) -> AppClients:
    return cast(AppClients, request.app.state.clients)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    clients = get_clients(request)
    async with clients.db.session() as session:
        yield session
