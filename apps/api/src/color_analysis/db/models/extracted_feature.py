import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from color_analysis.db.base import Base


class ExtractedFeature(Base):
    __tablename__ = "extracted_features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), index=True
    )
    region: Mapped[str] = mapped_column(String(32))
    l_star: Mapped[float] = mapped_column(Float)
    a_star: Mapped[float] = mapped_column(Float)
    b_star: Mapped[float] = mapped_column(Float)
    c_star: Mapped[float] = mapped_column(Float)
    h_deg: Mapped[float] = mapped_column(Float)
    ita_deg: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
