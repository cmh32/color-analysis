"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anonymous_token", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anonymous_token"),
    )

    op.create_table(
        "analysis_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_state", sa.String(length=64), nullable=True),
        sa.Column("reliability", sa.Numeric(4, 3), nullable=True),
        sa.Column("reliability_bucket", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "photo_quality",
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("blur_score", sa.Float(), nullable=False),
        sa.Column("exposure_score", sa.Float(), nullable=False),
        sa.Column("face_count", sa.Integer(), nullable=False),
        sa.Column("yaw_degrees", sa.Float(), nullable=False),
        sa.Column("pitch_degrees", sa.Float(), nullable=False),
        sa.Column("reasons", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id"),
    )

    op.create_table(
        "extracted_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("l_star", sa.Float(), nullable=False),
        sa.Column("a_star", sa.Float(), nullable=False),
        sa.Column("b_star", sa.Float(), nullable=False),
        sa.Column("c_star", sa.Float(), nullable=False),
        sa.Column("h_deg", sa.Float(), nullable=False),
        sa.Column("ita_deg", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "aggregated_features",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_name", sa.String(length=64), nullable=False),
        sa.Column("feature_value", sa.Float(), nullable=False),
        sa.Column("spread", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "feature_name"),
    )

    op.create_table(
        "classification",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("primary_season", sa.String(length=16), nullable=False),
        sa.Column("secondary_season", sa.String(length=16), nullable=False),
        sa.Column("scorecard", sa.JSON(), nullable=False),
        sa.Column("probabilities", sa.JSON(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("reliability_bucket", sa.String(length=16), nullable=False),
        sa.Column("result_state", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "audit_trace",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "stage"),
    )

    op.create_index("ix_analysis_sessions_expires_at", "analysis_sessions", ["expires_at"])
    op.create_index("ix_photos_session_id", "photos", ["session_id"])
    op.create_index("ix_extracted_features_photo_id", "extracted_features", ["photo_id"])


def downgrade() -> None:
    op.drop_table("audit_trace")
    op.drop_table("classification")
    op.drop_table("aggregated_features")
    op.drop_table("extracted_features")
    op.drop_table("photo_quality")
    op.drop_table("photos")
    op.drop_table("analysis_sessions")
    op.drop_table("users")
