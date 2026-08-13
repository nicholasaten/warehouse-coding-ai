import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoryRackMapping(Base):
    """Maps the free-text 'Category Rack' value that shows up in raw uploaded
    location data (e.g. "DRUGS", "COLD STORAGE", "ALL") to a
    LocationTypeConfig, scoped by `warehouse_type_code` since LocType
    meanings differ by scheme (see LocationTypeConfig). Several raw category
    texts can map to the same LocType within one scheme (e.g. both "DRUGS"
    and "CONSUMABLES" map to Non-General LocType A) -- kept as its own
    admin-editable table rather than hardcoded in the rule engine, since new
    raw category spellings will keep showing up as more hospitals' data
    gets uploaded."""

    __tablename__ = "category_rack_mappings"
    __table_args__ = (
        UniqueConstraint("warehouse_type_code", "raw_category_text", name="uq_category_rack_per_wh_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    warehouse_type_code: Mapped[str] = mapped_column(String(2))
    raw_category_text: Mapped[str] = mapped_column(String(100))
    location_type_config_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("location_type_configs.id"))
