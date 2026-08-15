"""The PIC review/revision workflow (AI Warehouse system's "suggest, never
auto-apply" pattern applied to PIC edits, not just AI suggestions): a PIC
never writes to `warehouses`/`locations` directly, they submit a Revision
proposing new values for a fixed, deliberately small set of descriptive
fields. Only formula-INDEPENDENT fields are revisable -- site_id,
warehouse_type_code, warehouse_code, duplicate_letter, location_type_code,
seq, and generated_code all stay Admin-only (via the PATCH endpoints in
warehouses.py/locations.py), never part of this workflow, because letting a
revision touch them could desync the deterministic ID formula from the
actual row.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.revision import Revision
from app.models.warehouse import Warehouse

REVISABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "warehouse": ("name", "description", "capacity"),
    "location": ("description", "category_rack_raw"),
}
ENTITY_MODELS: dict[str, type] = {"warehouse": Warehouse, "location": Location}


def get_entity(db: Session, entity_type: str, entity_id: uuid.UUID) -> Warehouse | Location:
    if entity_type not in ENTITY_MODELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown entity_type")
    entity = db.get(ENTITY_MODELS[entity_type], entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_type.title()} not found")
    return entity


def _validate_value_keys(entity_type: str, value: dict[str, Any]) -> None:
    allowed = REVISABLE_FIELDS[entity_type]
    unknown = set(value) - set(allowed)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fields {sorted(unknown)} are not revisable for {entity_type} (only {list(allowed)} are)",
        )


def entity_site_id(db: Session, entity_type: str, entity: Warehouse | Location) -> uuid.UUID:
    """Resolves the owning Site for scope checks -- direct for a Warehouse,
    through its Warehouse for a Location, same pattern as the list/get
    endpoints in warehouses.py/locations.py."""
    if entity_type == "warehouse":
        return entity.site_id
    warehouse = db.get(Warehouse, entity.warehouse_id)
    return warehouse.site_id


def submit_revision(
    db: Session,
    submitted_by: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    proposed_value: dict[str, Any],
    comment: str,
) -> Revision:
    entity = get_entity(db, entity_type, entity_id)
    _validate_value_keys(entity_type, proposed_value)
    if not proposed_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="proposed_value cannot be empty")

    original_value = {field: getattr(entity, field) for field in proposed_value}
    revision = Revision(
        entity_type=entity_type,
        entity_id=entity_id,
        submitted_by=submitted_by,
        original_value=original_value,
        proposed_value=proposed_value,
        comment=comment,
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return revision


def list_revisions(
    db: Session,
    status_filter: str | None = None,
    entity_type: str | None = None,
    submitted_by: uuid.UUID | None = None,
) -> list[Revision]:
    query = select(Revision).order_by(Revision.submitted_at.desc())
    if status_filter:
        query = query.where(Revision.status == status_filter)
    if entity_type:
        query = query.where(Revision.entity_type == entity_type)
    if submitted_by:
        query = query.where(Revision.submitted_by == submitted_by)
    return list(db.scalars(query).all())


def _get_pending_revision(db: Session, revision_id: uuid.UUID) -> Revision:
    revision = db.get(Revision, revision_id)
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    if revision.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Revision already reviewed")
    return revision


def _apply_value(entity: Warehouse | Location, value: dict[str, Any]) -> None:
    for field, new_value in value.items():
        setattr(entity, field, new_value)
    # The coding just changed -- any earlier PIC acknowledgment no longer
    # reflects what's actually there, so it needs to be re-confirmed.
    entity.pic_acknowledged_at = None
    entity.pic_acknowledged_by = None


def approve_revision(db: Session, revision_id: uuid.UUID, reviewed_by: uuid.UUID) -> Revision:
    revision = _get_pending_revision(db, revision_id)
    entity = get_entity(db, revision.entity_type, revision.entity_id)
    _apply_value(entity, revision.proposed_value)
    revision.final_value = revision.proposed_value
    revision.status = "approved"
    revision.reviewed_by = reviewed_by
    revision.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(revision)
    return revision


def reject_revision(db: Session, revision_id: uuid.UUID, reviewed_by: uuid.UUID, reason: str) -> Revision:
    revision = _get_pending_revision(db, revision_id)
    revision.status = "rejected"
    revision.rejection_reason = reason
    revision.reviewed_by = reviewed_by
    revision.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(revision)
    return revision


def edit_and_approve_revision(
    db: Session, revision_id: uuid.UUID, reviewed_by: uuid.UUID, final_value: dict[str, Any]
) -> Revision:
    """Admin modifies the PIC's proposal before applying it -- `final_value`
    is stored separately from `proposed_value` so the history stays honest
    about what was actually asked for vs. what was actually applied."""
    revision = _get_pending_revision(db, revision_id)
    _validate_value_keys(revision.entity_type, final_value)
    if not final_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="final_value cannot be empty")
    entity = get_entity(db, revision.entity_type, revision.entity_id)
    _apply_value(entity, final_value)
    revision.final_value = final_value
    revision.status = "approved"
    revision.reviewed_by = reviewed_by
    revision.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(revision)
    return revision
