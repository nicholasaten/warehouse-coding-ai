import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MergeSuggestion(Base):
    """AI Responsibility #3/#5 (mapping, duplicate detection) -- when an
    uploaded location's description doesn't exactly match an existing one in
    the same (warehouse, location_type) but is textually SIMILAR, the raw
    row is held here instead of being auto-created as a new Location.
    Nothing merges automatically (explicit decision, see README) -- an
    admin must approve (the raw row really is the same place, no new
    Location is created) or reject (it's genuinely different, and the held
    row is created as a new Location the normal way).

    `similarity_score` and `reasoning` exist so the suggestion is always
    explainable, not just a bare yes/no -- the brief explicitly requires
    every AI recommendation to include its reasoning.
    """

    __tablename__ = "merge_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_merge_suggestion_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    upload_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="CASCADE"))
    location_type_code: Mapped[str] = mapped_column(String(2))
    # The raw, held row -- not yet a Location. Created as one only on reject.
    raw_category_rack: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_description: Mapped[str] = mapped_column(String(500))
    suggested_location_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("locations.id", ondelete="CASCADE"))
    similarity_score: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
