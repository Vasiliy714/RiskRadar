"""add core tables

Revision ID: e71ee972dcd9
Revises: 5a4d2ad3ad98
Create Date: 2026-05-24 20:57:15.819466

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e71ee972dcd9"
down_revision: str | Sequence[str] | None = "5a4d2ad3ad98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "documents",
        sa.Column("issuer_id", sa.UUID(), nullable=True),
        sa.Column(
            "doc_type",
            sa.Enum(
                "annual_report",
                "quarterly_report",
                "news",
                "legal_case",
                "rating_report",
                "press_release",
                name="document_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["issuer_id"],
            ["issuers.id"],
            name=op.f("fk_documents_issuer_id_issuers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_table(
        "risk_reports",
        sa.Column("issuer_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "completed",
                "requires_review",
                "failed",
                name="risk_report_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "risk_level",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="risk_level",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["issuer_id"],
            ["issuers.id"],
            name=op.f("fk_risk_reports_issuer_id_issuers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_reports")),
    )
    op.create_table(
        "agent_traces",
        sa.Column("risk_report_id", sa.UUID(), nullable=False),
        sa.Column(
            "agent_name",
            sa.Enum(
                "report_agent",
                "news_agent",
                "market_agent",
                "legal_agent",
                "rating_agent",
                "supervisor",
                name="agent_name",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["risk_report_id"],
            ["risk_reports.id"],
            name=op.f("fk_agent_traces_risk_report_id_risk_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_traces")),
    )
    op.create_table(
        "ingestion_jobs",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "failed",
                name="ingestion_job_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_ingestion_jobs_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ingestion_jobs")
    op.drop_table("agent_traces")
    op.drop_table("risk_reports")
    op.drop_table("documents")
