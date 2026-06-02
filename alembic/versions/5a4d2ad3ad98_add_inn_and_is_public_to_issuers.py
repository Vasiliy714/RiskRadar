"""add inn and is_public to issuers

Revision ID: 5a4d2ad3ad98
Revises: 84c7fa5d5fd6
Create Date: 2026-05-24 19:26:42.160884

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "5a4d2ad3ad98"
down_revision: str | Sequence[str] | None = "84c7fa5d5fd6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
