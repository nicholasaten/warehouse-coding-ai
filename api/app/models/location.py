import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Reserved sequence number for the generic "uncategorized / not yet sorted"
# bucket -- confirmed from the real RSUS Mapping data, where several
# unrelated raw racks (no clear category) all collapsed into one
# "STAGING RECEIVE" location per warehouse, always at seq 99 regardless of
# how many distinct locations that warehouse otherwise has. Never assigned
# by the normal sequential counter.
STAGING_RECEIVE_SEQ = 99
STAGING_RECEIVE_DESCRIPTION = "STAGING RECEIVE"


class Location(Base):
    """`generated_code` = `{site.short_code}{warehouse.warehouse_type_code}
    {warehouse.warehouse_code}{warehouse.duplicate_letter or ''}-
    {location_type_code}{seq:02d}`, always derived by `id_generator_service`,
    never typed in directly.

    `seq` is sequential per (warehouse, location_type_code) in order of
    first appearance among DISTINCT final descriptions -- multiple raw racks
    that describe the same real place (e.g. two differently-worded "DRUGS -
    PSIKOTROPIKA" racks from two legacy stores) share one Location row, not
    one each. That deduplication is the AI-assisted merge step -- see
    RawLocationEntry."""

    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "location_type_code", "seq", name="uq_location_formula_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="CASCADE"))
    location_type_code: Mapped[str] = mapped_column(String(2))
    seq: Mapped[int] = mapped_column(Integer)
    generated_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    # The raw "Category Rack" text this location's LocType was mapped from
    # (e.g. "DRUGS") -- kept for traceability even though location_type_code
    # is what the ID actually encodes.
    category_rack_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Free-form position/size on the per-Warehouse visual Layout canvas --
    # purely a display concern, never read by id_generator_service or any
    # formula logic. NULL means "not yet placed on the canvas" (the
    # frontend auto-arranges those into a grid on first load rather than
    # stacking them at 0,0). No grid-snapping -- width/height are whatever
    # the admin dragged them to, matching the real floor-plan reference
    # the layout feature was modeled on.
    layout_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    layout_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    layout_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    layout_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Same "needs PIC review" semantics as Warehouse.pic_acknowledged_at --
    # see that column's comment.
    pic_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pic_acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
