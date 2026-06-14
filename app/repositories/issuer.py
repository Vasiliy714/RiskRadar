import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.issuer import Issuer
from app.schemas.issuer import IssuerCreate, IssuerUpdate


class IssuerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: IssuerCreate) -> Issuer:
        issuer = Issuer(**data.model_dump())
        self._session.add(issuer)
        await self._session.flush()
        await self._session.refresh(issuer)
        return issuer

    async def get_by_id(self, id: uuid.UUID) -> Issuer | None:
        return await self._session.get(Issuer, id)

    async def get_by_code(self, code: str) -> Issuer | None:
        result = await self._session.execute(
            select(Issuer).where(Issuer.code == code),
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        is_public: bool | None = None,
    ) -> tuple[list[Issuer], int]:
        stmt = select(Issuer)
        count_stmt = select(func.count()).select_from(Issuer)

        if is_public is not None:
            stmt = stmt.where(Issuer.is_public == is_public)
            count_stmt = count_stmt.where(Issuer.is_public == is_public)

        stmt = (
            stmt.order_by(Issuer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.execute(stmt)).scalars().all())
        total = (await self._session.execute(count_stmt)).scalar_one()
        return items, total

    async def update(self, issuer: Issuer, data: IssuerUpdate) -> Issuer:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(issuer, field, value)
        await self._session.flush()
        await self._session.refresh(issuer)
        return issuer

    async def delete(self, issuer: Issuer) -> None:
        await self._session.delete(issuer)
        await self._session.flush()
