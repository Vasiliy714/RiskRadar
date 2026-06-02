import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AgentName, RiskReportStatus
from app.db.models.agent_trace import AgentTrace
from app.db.models.issuer import Issuer
from app.db.models.risk_report import RiskReport


@pytest.mark.integration
async def test_issuer_crud(async_client: httpx.AsyncClient) -> None:
    from app.main import app

    clients = app.state.clients
    code = f"CASCADE_{uuid.uuid4().hex[:8]}"
    async with clients.db.session() as session:
        issuer = Issuer(
            code=code,
            name="Sberbank",
            inn="7707083893",
            is_public=True,
            country_code="RU",
            sector="BANK",
        )
        session.add(issuer)
        await session.commit()
        await session.refresh(issuer)

        assert issuer.id is not None
        assert issuer.created_at is not None

        result = await session.execute(select(Issuer).where(Issuer.code == code))
        loaded = result.scalar_one()
        assert loaded.name == "Sberbank"

        await session.delete(loaded)
        await session.commit()


@pytest.mark.integration
async def test_cascade_delete_report_traces(async_client: httpx.AsyncClient) -> None:
    """Удаление RiskReport каскадом сносит свои AgentTrace."""
    from app.main import app

    clients = app.state.clients
    code = f"CASCADE_{uuid.uuid4().hex[:8]}"
    async with clients.db.session() as session:
        issuer = Issuer(code=code, name="Cascade Test")
        report = RiskReport(issuer=issuer, status=RiskReportStatus.RUNNING)
        report.agent_traces = [
            AgentTrace(agent_name=AgentName.NEWS_AGENT, input_payload={"step": 1}),
            AgentTrace(agent_name=AgentName.LEGAL_AGENT, input_payload={"step": 2}),
        ]
        session.add(issuer)
        await session.commit()
        issuer_id = issuer.id
        report_id = report.id
        await session.delete(report)
        await session.commit()
        trace_count = await session.scalar(
            select(func.count())
            .select_from(AgentTrace)
            .where(AgentTrace.risk_report_id == report_id)
        )
        assert trace_count == 0
        loaded_issuer = await session.get(Issuer, issuer_id)
        assert loaded_issuer is not None

        await session.delete(loaded_issuer)
        await session.commit()


@pytest.mark.integration
async def test_restrict_delete_issuer_with_reports(async_client: httpx.AsyncClient) -> None:
    """Нельзя удалить Issuer, y которого есть RiskReport (ondelete=RESTRICT)."""
    from app.main import app

    clients = app.state.clients
    code = f"CASCADE_{uuid.uuid4().hex[:8]}"
    async with clients.db.session() as session:
        issuer = Issuer(code=code, name="Restrict Test")
        report = RiskReport(issuer=issuer, status=RiskReportStatus.COMPLETED)
        session.add(issuer)
        await session.commit()

        issuer_id = issuer.id
        report_id = report.id

        await session.delete(issuer)
        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()

        assert await session.get(Issuer, issuer_id) is not None
        assert await session.get(RiskReport, report_id) is not None

        report = await session.get(RiskReport, report_id)
        await session.delete(report)
        await session.commit()
        issuer = await session.get(Issuer, issuer_id)
        await session.delete(issuer)
        await session.commit()


@pytest.fixture
async def db_session(
    async_client: httpx.AsyncClient,
) -> AsyncGenerator[AsyncSession, None]:
    from app.main import app
    async with app.state.clients.db.session() as session:
        yield session
        await session.rollback()
