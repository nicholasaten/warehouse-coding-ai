import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UploadBatch(Base):
    """One row per Excel file uploaded. `status` is set directly to its final
    value since processing happens synchronously within the request."""

    __tablename__ = "upload_batches"
    __table_args__ = (
        CheckConstraint("file_type IN ('warehouse_master', 'location_master')", name="chk_upload_batch_file_type"),
        CheckConstraint("status IN ('processing', 'completed', 'failed')", name="chk_upload_batch_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    file_type: Mapped[str] = mapped_column(String(20))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    # A row that looked like a possible duplicate of an existing location
    # (see MergeSuggestion) is neither a success nor an error -- it's held
    # for admin review, not silently created or silently rejected.
    pending_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
