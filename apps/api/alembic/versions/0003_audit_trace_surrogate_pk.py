"""replace audit_trace composite PK with surrogate UUID id

Revision ID: 0003_audit_trace_surrogate_pk
Revises: 0002_session_reliability_float
Create Date: 2026-04-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_audit_trace_surrogate_pk"
down_revision = "0002_session_reliability_float"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("audit_trace_pkey", "audit_trace", type_="primary")
    op.add_column(
        "audit_trace",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_primary_key("audit_trace_pkey", "audit_trace", ["id"])
    op.alter_column("audit_trace", "id", server_default=None)
    op.create_index("ix_audit_trace_session_id_stage", "audit_trace", ["session_id", "stage"])


def downgrade() -> None:
    op.drop_index("ix_audit_trace_session_id_stage", "audit_trace")
    op.drop_constraint("audit_trace_pkey", "audit_trace", type_="primary")
    op.drop_column("audit_trace", "id")
    op.create_primary_key("audit_trace_pkey", "audit_trace", ["session_id", "stage"])
