import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from color_analysis.db.base import Base


class PhotoQuality(Base):
    __tablename__ = "photo_quality"

    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
    accepted: Mapped[bool] = mapped_column(Boolean)
    blur_score: Mapped[float] = mapped_column(Float)
    exposure_score: Mapped[float] = mapped_column(Float)
    face_count: Mapped[int] = mapped_column(Integer)
    yaw_degrees: Mapped[float] = mapped_column(Float)
    pitch_degrees: Mapped[float] = mapped_column(Float)
    reasons: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
