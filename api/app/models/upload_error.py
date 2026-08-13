import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UploadError(Base):
    """One row per rejected cell/row, so Admin gets 'row 14, column Warehouse
    Code: ...' instead of a generic failure count."""

    __tablename__ = "upload_errors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("upload_batches.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(String(500))
