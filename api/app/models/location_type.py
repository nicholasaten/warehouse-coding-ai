import uuid

from sqlalchemy import Boolean, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocationTypeConfig(Base):
    """Fixed business rule (SOP), admin-configured only -- the single letter
    that appears right after the hyphen in every Location ID.

    Scoped to `warehouse_type_code` the same way WarehouseCodeConfig is --
    confirmed by real data that the same letter means different things
    under different warehouse types: under Non-General (A), A=Drugs/
    Consumables ... H=All; under General (B), A=Rak, B=All. A location's
    LocType is only ever chosen from the set that matches its warehouse's
    own warehouse_type_code.

    `is_whole_warehouse` marks whichever code means "All" for that scheme --
    confirmed by real data, an "All" location code omits its trailing
    sequence number entirely (e.g. "USB12-B", not "USB12-B01"), since
    there's only ever one such location per warehouse."""

    __tablename__ = "location_type_configs"
    __table_args__ = (UniqueConstraint("warehouse_type_code", "code", name="uq_loc_type_per_wh_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    warehouse_type_code: Mapped[str] = mapped_column(String(2))
    code: Mapped[str] = mapped_column(String(2))
    description: Mapped[str] = mapped_column(String(255))
    is_whole_warehouse: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
