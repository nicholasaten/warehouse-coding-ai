import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Revision(Base):
    """A PIC's proposed change to a Warehouse or Location's descriptive
    fields -- PICs never write to `warehouses`/`locations` directly (see
    app/routers/warehouses.py, locations.py), this is their only path.

    `original_value`/`proposed_value` are JSON snapshots of just the
    revisable fields (never the formula-driving ones -- site_id, type/code,
    duplicate_letter, seq, generated_code -- those stay Admin-only via the
    PATCH endpoints, not part of this workflow at all). `final_value` is
    null until reviewed; on approve it equals `proposed_value`, but on
    Edit & Approve the admin may have changed it before applying, so it's
    stored separately to keep an honest history of what was actually
    applied vs. what was originally asked for.
    """

    __tablename__ = "revisions"
    __table_args__ = (
        CheckConstraint("entity_type IN ('warehouse', 'location')", name="chk_revision_entity_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_revision_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    submitted_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    original_value: Mapped[dict] = mapped_column(JSON)
    proposed_value: Mapped[dict] = mapped_column(JSON)
    comment: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    final_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
