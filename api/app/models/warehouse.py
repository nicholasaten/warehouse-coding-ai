import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Warehouse(Base):
    """`generated_code` is always derived by `id_generator_service` from
    `site_id` + `warehouse_type_code` + `warehouse_code` + `duplicate_letter`
    -- never typed in directly -- but it's stored (not computed on read) so
    historical codes stay stable even if config descriptions change later.

    `duplicate_letter` is null unless 2+ warehouses share the same
    (site, warehouse_type_code, warehouse_code) -- only then does the
    formula call for a disambiguating suffix (A, B, ...), matching the real
    data (`RSUS-A02` has none; `RSUS-A01A` does, because a second Pharmacy
    Mainstore warehouse -- Consumables -- exists under the same type+code)."""

    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "warehouse_type_code", "warehouse_code", "duplicate_letter", name="uq_warehouse_formula_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sites.id"))
    warehouse_type_code: Mapped[str] = mapped_column(String(2))
    warehouse_code: Mapped[str] = mapped_column(String(2))
    duplicate_letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    generated_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
