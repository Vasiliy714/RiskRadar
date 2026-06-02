from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.risk_report import RiskReport

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Issuer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "issuers"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
    )
    country_code: Mapped[str | None] = mapped_column(String(2))
    sector: Mapped[str | None] = mapped_column(String(128))

    documents: Mapped[list[Document]] = relationship(
        back_populates="issuer",
        passive_deletes=True,
    )
    risk_reports: Mapped[list[RiskReport]] = relationship(
        back_populates="issuer",
        passive_deletes=True,
    )
