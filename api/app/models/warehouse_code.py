import uuid

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WarehouseCodeConfig(Base):
    """Fixed business rule (SOP), admin-configured only. `code` is a 2-digit
    number scoped to a `warehouse_type_code` -- the same number means
    something different under each WH Type (e.g. "01" is "Medical" under
    General Items but "Pharmacy Mainstore" under Non-General Items), which
    is why this isn't a single flat lookup table."""

    __tablename__ = "warehouse_code_configs"
    __table_args__ = (UniqueConstraint("warehouse_type_code", "code", name="uq_wh_code_per_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    warehouse_type_code: Mapped[str] = mapped_column(String(2))
    code: Mapped[str] = mapped_column(String(2))
    description: Mapped[str] = mapped_column(String(255))
