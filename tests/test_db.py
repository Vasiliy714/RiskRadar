import httpx
import pytest


@pytest.mark.integration
async def test_issuer_crud(async_client: httpx.AsyncClient) -> None:
    from sqlalchemy import select

    from app.db.models import Issuer
    from app.main import app

    clients = app.state.clients
    async with clients.db.session() as session:
        issuer = Issuer(
            ticker="SBER",
            name="Sberbank",
            inn="7707083893",
            country_code="RU",
            sector="BANK",
            is_public=True,
        )
        session.add(issuer)
        await session.commit()
        await session.refresh(issuer)

        assert issuer.id is not None
        assert issuer.created_at is not None

        result = await session.execute(select(Issuer).where(Issuer.ticker == "SBER"))
        loaded = result.scalar_one()
        assert loaded.name == "Sberbank"

        await session.delete(loaded)
        await session.commit()
