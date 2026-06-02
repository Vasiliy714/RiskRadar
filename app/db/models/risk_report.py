from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.agent_trace import AgentTrace
    from app.db.models.issuer import Issuer

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum_values
from app.db.enums import RiskLevel, RiskReportStatus


class RiskReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "risk_reports"

    issuer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issuers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[RiskReportStatus] = mapped_column(
        SAEnum(
            RiskReportStatus,
            native_enum=False,
            name="risk_report_status",
            values_callable=str_enum_values,
        ),
        nullable=False,
        default=RiskReportStatus.RUNNING,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        SAEnum(
            RiskLevel,
            native_enum=False,
            name="risk_level",
            values_callable=str_enum_values,
        ),
    )
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text)

    issuer: Mapped[Issuer] = relationship(back_populates="risk_reports")
    agent_traces: Mapped[list[AgentTrace]] = relationship(
        back_populates="risk_report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name="risk_score_range",
        ),
        CheckConstraint(
            "coverage_penalty IS NULL OR (coverage_penalty >= 0 AND coverage_penalty <= 1)",
            name="coverage_penalty_range",
        ),
    )
