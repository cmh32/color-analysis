import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from color_analysis.db.base import Base


class Classification(Base):
    __tablename__ = "classification"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    primary_season: Mapped[str] = mapped_column(String(16))
    secondary_season: Mapped[str] = mapped_column(String(16))
    scorecard: Mapped[dict[str, float]] = mapped_column(JSON)
    probabilities: Mapped[dict[str, float]] = mapped_column(JSON)
    reliability: Mapped[float] = mapped_column(Float)
    reliability_bucket: Mapped[str] = mapped_column(String(16))
    result_state: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
