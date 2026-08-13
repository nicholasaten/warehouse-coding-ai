import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WarehouseTypeConfig(Base):
    """Fixed business rule (SOP), admin-configured only -- the AI/rule engine
    reads this table, never writes to it. `code` is the single letter that
    appears right after the Site in every Warehouse ID (e.g. A/B/C).
    Example seed data from the company's real formula: A=Non-General Items,
    B=General Items, C=Transit."""

    __tablename__ = "warehouse_type_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(2), unique=True)
    description: Mapped[str] = mapped_column(String(255))
