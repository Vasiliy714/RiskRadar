"""add score checks and rename input column

Revision ID: 1347cbde6c60
Revises: 431f85a692f4
Create Date: 2026-05-28 17:40:21.928770

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1347cbde6c60'
down_revision: str | Sequence[str] | None = '431f85a692f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_risk_reports_risk_score_range",
        "risk_reports",
        "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
    )
    op.create_check_constraint(
        "ck_risk_reports_coverage_penalty_range",
        "risk_reports",
        "coverage_penalty IS NULL OR (coverage_penalty >= 0 AND coverage_penalty <= 1)",
    )
    op.alter_column(
        "agent_traces",
        "input_",
        new_column_name="input",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "agent_traces",
        "input",
        new_column_name="input_",
    )
    op.drop_constraint(
        "ck_risk_reports_coverage_penalty_range",
        "risk_reports",
        type_="check",
    )
    op.drop_constraint(
        "ck_risk_reports_risk_score_range",
        "risk_reports",
        type_="check",
    )
