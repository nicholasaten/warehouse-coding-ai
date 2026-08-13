import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ROLE_VALUES = ("admin", "pic")


class User(Base):
    """Two roles now, added for the Warehouse & Location Review Workflow
    feature: `admin` (unscoped, can create/edit warehouses & locations
    directly, reviews PIC revision requests) and `pic` (scoped to exactly
    one `site_id` -- a Hospital Unit's PIC -- can only view their own
    site's data and submit revision requests, never edit directly). The
    CHECK constraint keeps this consistent at the database level: an admin
    always has site_id NULL, a pic always has one set. This is a
    single-table constraint (both columns live on this same row), so a
    plain CHECK works here -- unlike a few cross-table invariants
    elsewhere in this project's sibling apps that needed a trigger
    instead."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'admin' AND site_id IS NULL) OR (role = 'pic' AND site_id IS NOT NULL)",
            name="chk_user_role_site_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="admin", server_default="admin")
    site_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("sites.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
