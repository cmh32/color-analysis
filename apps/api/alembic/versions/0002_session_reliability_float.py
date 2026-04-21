"""change analysis_sessions.reliability from Numeric to Float

Revision ID: 0002_session_reliability_float
Revises: 0001_initial
Create Date: 2026-04-20

"""

from alembic import op
import sqlalchemy as sa

revision = "0002_session_reliability_float"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "analysis_sessions",
        "reliability",
        existing_type=sa.Numeric(4, 3),
        type_=sa.Float(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "analysis_sessions",
        "reliability",
        existing_type=sa.Float(),
        type_=sa.Numeric(4, 3),
        existing_nullable=True,
    )
