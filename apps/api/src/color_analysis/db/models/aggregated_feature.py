import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from color_analysis.db.base import Base


class AggregatedFeature(Base):
    __tablename__ = "aggregated_features"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    feature_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    feature_value: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
