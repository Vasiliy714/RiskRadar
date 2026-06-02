"""add document indexes

Revision ID: 966beec7a0bb
Revises: 1347cbde6c60
Create Date: 2026-05-28 17:47:51.042877

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '966beec7a0bb'
down_revision: str | Sequence[str] | None = '1347cbde6c60'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column("documents", sa.Column("content_hash", sa.String(length=64), nullable=False))
    op.create_index(
        "ix_documents_issuer_type_current",
        "documents",
        ["issuer_id", "doc_type", "is_current"],
    )
    op.create_index("ix_documents_issuer_published", "documents", ["issuer_id", "published_at"])
    op.create_unique_constraint("uq_documents_content_hash", "documents", ["content_hash"])


def downgrade() -> None:
    op.drop_constraint("uq_documents_content_hash", "documents", type_="unique")
    op.drop_index("ix_documents_issuer_published", table_name="documents")
    op.drop_index("ix_documents_issuer_type_current", table_name="documents")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "is_current")
