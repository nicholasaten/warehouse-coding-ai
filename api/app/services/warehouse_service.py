"""Creating a warehouse is stateful, not just a formatting call: whether a
duplicate_letter suffix applies to the WHOLE (site, warehouse_type_code,
warehouse_code) group depends on how many warehouses share it (see
id_generator_service.assign_duplicate_letters). That means adding a second
warehouse to a group can rename the first one's generated_code -- this
module is where that side effect is applied and persisted, not just the
new row."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.revision import Revision
from app.models.site import Site
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.id_generator_service import assign_duplicate_letters, format_warehouse_code
from app.services.location_service import reassign_location_warehouse


def create_warehouse(
    db: Session,
    site_id: uuid.UUID,
    warehouse_type_code: str,
    warehouse_code: str,
    name: str,
    description: str | None,
    capacity: int | None,
) -> Warehouse:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown site")

    if not db.scalar(select(WarehouseTypeConfig).where(WarehouseTypeConfig.code == warehouse_type_code)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown warehouse_type_code")
    if not db.scalar(
        select(WarehouseCodeConfig).where(
            WarehouseCodeConfig.warehouse_type_code == warehouse_type_code,
            WarehouseCodeConfig.code == warehouse_code,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{warehouse_code}' is not a configured warehouse_code under type '{warehouse_type_code}'",
        )

    existing = list(
        db.scalars(
            select(Warehouse)
            .where(
                Warehouse.site_id == site_id,
                Warehouse.warehouse_type_code == warehouse_type_code,
                Warehouse.warehouse_code == warehouse_code,
            )
            .order_by(Warehouse.created_at)
        ).all()
    )

    new_warehouse = Warehouse(
        site_id=site_id,
        warehouse_type_code=warehouse_type_code,
        warehouse_code=warehouse_code,
        name=name,
        description=description,
        capacity=capacity,
        generated_code="",  # placeholder, set below once letters are assigned
    )

    group = existing + [new_warehouse]
    letters = assign_duplicate_letters(len(group))
    for warehouse, letter in zip(group, letters):
        warehouse.duplicate_letter = letter
        warehouse.generated_code = format_warehouse_code(site.code, warehouse_type_code, warehouse_code, letter)

    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)
    return new_warehouse


def acknowledge_warehouse(db: Session, warehouse_id: uuid.UUID, acknowledged_by: uuid.UUID) -> Warehouse:
    """The PIC for this Warehouse's Hospital Unit confirms they've
    reviewed its current coding and agree with it. Cleared back to
    "needs review" by any subsequent edit -- see _apply_value in
    revision_service.py and update_warehouse's PATCH endpoint -- since an
    old acknowledgment stops meaning anything once the coding changes."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    warehouse.pic_acknowledged_at = datetime.now(timezone.utc)
    warehouse.pic_acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(warehouse)
    return warehouse


def delete_warehouse(db: Session, warehouse_id: uuid.UUID) -> None:
    """Hard delete -- its Locations and MergeSuggestions cascade away at
    the DB level, and any raw-import suggestion audit rows that created it
    just lose that back-reference (SET NULL) rather than being destroyed
    (see migration 0009). Blocked while a Revision is still pending on it,
    so a PIC's in-flight request never ends up pointing at nothing.

    Deliberately does NOT re-letter any sibling warehouses left in the
    same (site, type, code) group -- e.g. deleting RSUS-A01A out of an
    A01A/A01B pair leaves A01B as "B" even though it's now the only one.
    Re-lettering would change that survivor's `generated_code`, and this
    system has no path today for cascading that into its already-created
    Locations' own codes (a pre-existing gap in create_warehouse's own
    relettering step, not something introduced here) -- so the safe
    choice is to leave existing codes alone rather than risk producing
    codes that silently disagree with the formula."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    pending = db.scalar(
        select(Revision).where(
            Revision.entity_type == "warehouse", Revision.entity_id == warehouse_id, Revision.status == "pending"
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This warehouse has a pending revision request -- approve or reject it before deleting.",
        )

    db.delete(warehouse)
    db.commit()


def merge_warehouse(db: Session, source_warehouse_id: uuid.UUID, target_warehouse_id: uuid.UUID) -> Warehouse:
    """Merges `source` into `target`: moves every Location out of source
    into target (recoding each one through reassign_location_warehouse --
    never a raw copy), then hard-deletes the now-empty source. This is the
    "combine two warehouses into one" workflow -- it never re-letters or
    renames the target itself, it only relocates the source's Locations
    into it and retires the source, same as doing it Location-by-Location
    through the Reassign Warehouse action followed by a manual delete.

    Both warehouses must belong to the same Hospital Unit (site) -- merging
    across sites has no real-world meaning here, they're different physical
    buildings. Validates every Location can actually move (no pending
    Revision, its location_type_code is still configured under the
    target's warehouse_type_code, no whole-warehouse conflict) BEFORE
    moving any of them, so a failure partway through a large warehouse
    never leaves the merge half-done."""
    if source_warehouse_id == target_warehouse_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a warehouse into itself")

    source = db.get(Warehouse, source_warehouse_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    target = db.get(Warehouse, target_warehouse_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown target warehouse")

    if source.site_id != target.site_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge warehouses that belong to different Hospital Units",
        )

    pending = db.scalar(
        select(Revision).where(
            Revision.entity_type == "warehouse", Revision.entity_id == source_warehouse_id, Revision.status == "pending"
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This warehouse has a pending revision request -- approve or reject it before merging.",
        )

    locations = list(db.scalars(select(Location).where(Location.warehouse_id == source_warehouse_id)).all())

    for location in locations:
        loc_pending = db.scalar(
            select(Revision).where(
                Revision.entity_type == "location", Revision.entity_id == location.id, Revision.status == "pending"
            )
        )
        if loc_pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location '{location.generated_code}' has a pending revision request -- "
                f"approve or reject it before merging.",
            )

        loc_type = db.scalar(
            select(LocationTypeConfig).where(
                LocationTypeConfig.warehouse_type_code == target.warehouse_type_code,
                LocationTypeConfig.code == location.location_type_code,
            )
        )
        if loc_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location '{location.generated_code}' type '{location.location_type_code}' is not "
                f"configured under the target warehouse's type '{target.warehouse_type_code}'",
            )
        if loc_type.is_whole_warehouse:
            already_exists = db.scalar(
                select(Location).where(
                    Location.warehouse_id == target_warehouse_id,
                    Location.location_type_code == location.location_type_code,
                )
            )
            if already_exists is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The target warehouse already has a whole-warehouse location of type "
                    f"'{location.location_type_code}'",
                )

    for location in locations:
        reassign_location_warehouse(db, location.id, target_warehouse_id)

    delete_warehouse(db, source_warehouse_id)
    db.refresh(target)
    return target
