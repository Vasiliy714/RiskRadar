from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.risk_report import RiskReport

import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum_values
from app.db.enums import AgentName


class AgentTrace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_traces"

    risk_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[AgentName] = mapped_column(
        SAEnum(
            AgentName,
            native_enum=False,
            name="agent_name",
            values_callable=str_enum_values,
        ),
        nullable=False,
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        "input",
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "output",
        JSONB,
    )
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    risk_report: Mapped[RiskReport] = relationship(back_populates="agent_traces")
