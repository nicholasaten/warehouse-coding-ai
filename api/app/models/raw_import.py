import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawImportBatch(Base):
    """One upload of a legacy raw export (e.g. RSUS Raw.xlsx -- Organization/
    CodeStore/Store/CodeStoreRack/StoreRack/ActiveStoreRack, nothing like the
    formula's own fields). `site_id` is chosen explicitly at upload time
    rather than inferred from the file's free-text Organization column --
    which hospital this data belongs to is exactly the kind of thing that
    shouldn't be guessed."""

    __tablename__ = "raw_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sites.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RawWarehouseSuggestion(Base):
    """One CONSOLIDATED group of legacy (CodeStore, Store) rows from a raw
    import -- possibly several, if the AI's clustering step judged them to
    be billing/status variants of the same physical warehouse (e.g.
    "EMERGENCY" + "EMERGENCY NONCHARGEABLE"; confirmed against real
    RSUS Mapping.xlsx ground truth, where 61 legacy store names collapse
    into only 48 real final warehouses this way) -- carrying the AI's
    suggested Warehouse Type Code + Warehouse Code, both constrained to
    already-configured values only, the AI is never allowed to invent a new
    one (validated in raw_import_service, not just prompted for). Nothing is
    created until an admin approves (optionally overriding the suggestion
    first) or rejects.

    `legacy_code`/`legacy_name` are the PRIMARY (first) member of the
    group; `consolidated_legacy_names` lists any others folded in with it.
    `raw_rows` holds the UNION of every member's rack rows verbatim
    (captured at upload time) so location suggestions can be generated
    later, once this warehouse is actually approved and its real
    warehouse_type_code is known -- no need to re-upload or re-parse the
    original file."""

    __tablename__ = "raw_warehouse_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_raw_wh_suggestion_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("raw_import_batches.id", ondelete="CASCADE"))
    legacy_code: Mapped[str] = mapped_column(String(50))
    legacy_name: Mapped[str] = mapped_column(String(255))
    consolidated_legacy_names: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    raw_rows: Mapped[list] = mapped_column(JSON)
    suggested_warehouse_type_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    suggested_warehouse_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    created_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RawLocationSuggestion(Base):
    """One raw rack row's AI-suggested Category Rack mapping, generated only
    after its warehouse suggestion is approved (see generate_location_
    suggestions) -- so the valid Category Rack options can be scoped to the
    warehouse's now-known real type. Approving either creates a real
    Location, or -- if it turns out to be textually similar to one that
    already exists -- a MergeSuggestion instead, exactly like a normal
    Location Master upload would (`created_location_id` xor
    `created_merge_suggestion_id` is set, never both)."""

    __tablename__ = "raw_location_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_raw_loc_suggestion_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("raw_import_batches.id", ondelete="CASCADE"))
    warehouse_suggestion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("raw_warehouse_suggestions.id", ondelete="CASCADE")
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="CASCADE"))
    legacy_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    legacy_description: Mapped[str] = mapped_column(String(500))
    is_active_raw: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    suggested_category_rack: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    created_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    created_merge_suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("merge_suggestions.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
