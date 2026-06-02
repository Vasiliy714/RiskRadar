from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.ingestion_job import IngestionJob
    from app.db.models.issuer import Issuer

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum_values
from app.db.enums import DocumentType


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    issuer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issuers.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(
            DocumentType,
            native_enum=False,
            name="document_type",
            values_callable=str_enum_values,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    external_id: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    issuer: Mapped[Issuer | None] = relationship(back_populates="documents")
    ingestion_jobs: Mapped[list[IngestionJob]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("ix_documents_issuer_type_current", "issuer_id", "doc_type", "is_current"),
        Index("ix_documents_issuer_published", "issuer_id", "published_at"),
        UniqueConstraint("content_hash", name="uq_documents_content_hash"),
    )
