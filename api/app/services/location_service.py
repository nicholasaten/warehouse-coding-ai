import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import STAGING_RECEIVE_DESCRIPTION, Location
from app.models.location_type import LocationTypeConfig
from app.models.revision import Revision
from app.models.site import Site
from app.models.warehouse import Warehouse
from app.services.id_generator_service import format_location_code, next_location_sequence


def create_location(
    db: Session,
    warehouse_id: uuid.UUID,
    location_type_code: str,
    category_rack_raw: str | None,
    description: str,
) -> Location:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown warehouse")
    site = db.get(Site, warehouse.site_id)

    loc_type = db.scalar(
        select(LocationTypeConfig).where(
            LocationTypeConfig.warehouse_type_code == warehouse.warehouse_type_code,
            LocationTypeConfig.code == location_type_code,
        )
    )
    if loc_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{location_type_code}' is not a configured location_type under warehouse type "
            f"'{warehouse.warehouse_type_code}'",
        )

    if loc_type.is_whole_warehouse:
        already_exists = db.scalar(
            select(Location).where(
                Location.warehouse_id == warehouse_id, Location.location_type_code == location_type_code
            )
        )
        if already_exists is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This warehouse already has a whole-warehouse location of this type",
            )
        seq = None
    else:
        existing_seqs = list(
            db.scalars(
                select(Location.seq).where(
                    Location.warehouse_id == warehouse_id, Location.location_type_code == location_type_code
                )
            ).all()
        )
        is_staging_receive = description.strip().upper() == STAGING_RECEIVE_DESCRIPTION
        seq = next_location_sequence(existing_seqs, is_staging_receive)

    generated_code = format_location_code(
        site.short_code, warehouse.warehouse_type_code, warehouse.warehouse_code, warehouse.duplicate_letter,
        location_type_code, seq,
    )

    location = Location(
        warehouse_id=warehouse_id,
        location_type_code=location_type_code,
        seq=seq if seq is not None else 0,  # NULL wouldn't be enforceable by the unique constraint, see model note
        generated_code=generated_code,
        category_rack_raw=category_rack_raw,
        description=description,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def reassign_location_warehouse(db: Session, location_id: uuid.UUID, new_warehouse_id: uuid.UUID) -> Location:
    """Moves a Location into a different Warehouse without deleting/
    recreating it -- e.g. when combining two warehouses into one, so their
    Locations don't have to be rebuilt from scratch. Recomputes
    `generated_code`/`seq` through the exact same rules `create_location`
    uses, since the code embeds the warehouse's own type/code/duplicate
    letter. Blocked by a pending Revision, same guard as delete_location.

    `location_type_code` is scoped by `warehouse_type_code` (see
    LocationTypeConfig), so if the target warehouse is a different type than
    the one this Location came from, its location_type_code may no longer be
    valid there -- that's a 400, not a silent reinterpretation into whatever
    the new type's config happens to use for the same letter."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    pending = db.scalar(
        select(Revision).where(
            Revision.entity_type == "location", Revision.entity_id == location_id, Revision.status == "pending"
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This location has a pending revision request -- approve or reject it before reassigning.",
        )

    if new_warehouse_id == location.warehouse_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location is already in this warehouse")

    new_warehouse = db.get(Warehouse, new_warehouse_id)
    if new_warehouse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown warehouse")
    site = db.get(Site, new_warehouse.site_id)

    loc_type = db.scalar(
        select(LocationTypeConfig).where(
            LocationTypeConfig.warehouse_type_code == new_warehouse.warehouse_type_code,
            LocationTypeConfig.code == location.location_type_code,
        )
    )
    if loc_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{location.location_type_code}' is not a configured location_type under warehouse type "
            f"'{new_warehouse.warehouse_type_code}'",
        )

    if loc_type.is_whole_warehouse:
        already_exists = db.scalar(
            select(Location).where(
                Location.warehouse_id == new_warehouse_id,
                Location.location_type_code == location.location_type_code,
            )
        )
        if already_exists is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The target warehouse already has a whole-warehouse location of this type",
            )
        seq = None
    else:
        existing_seqs = list(
            db.scalars(
                select(Location.seq).where(
                    Location.warehouse_id == new_warehouse_id,
                    Location.location_type_code == location.location_type_code,
                )
            ).all()
        )
        is_staging_receive = location.description.strip().upper() == STAGING_RECEIVE_DESCRIPTION
        seq = next_location_sequence(existing_seqs, is_staging_receive)

    location.warehouse_id = new_warehouse_id
    location.seq = seq if seq is not None else 0
    location.generated_code = format_location_code(
        site.short_code, new_warehouse.warehouse_type_code, new_warehouse.warehouse_code, new_warehouse.duplicate_letter,
        location.location_type_code, seq,
    )
    db.commit()
    db.refresh(location)
    return location


def update_location_layout(
    db: Session, location_id: uuid.UUID, x: float, y: float, width: float, height: float
) -> Location:
    """Persists this Location's position/size on the free-form per-
    Warehouse Layout canvas. Purely a display concern -- never touches
    `generated_code` or any formula field, and doesn't check/block on a
    pending Revision the way edits to real data do, since this has no
    real-world meaning to review."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Width and height must be positive")

    location.layout_x = x
    location.layout_y = y
    location.layout_width = width
    location.layout_height = height
    db.commit()
    db.refresh(location)
    return location


def acknowledge_location(db: Session, location_id: uuid.UUID, acknowledged_by: uuid.UUID) -> Location:
    """The PIC for this Location's Hospital Unit confirms they've
    reviewed its current coding and agree with it. Same "cleared on any
    edit" semantics as acknowledge_warehouse."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    location.pic_acknowledged_at = datetime.now(timezone.utc)
    location.pic_acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(location)
    return location


def delete_location(db: Session, location_id: uuid.UUID) -> None:
    """Hard delete. Blocked while a Revision is still pending on it, same
    reasoning as delete_warehouse. Deliberately does NOT re-sequence any
    sibling locations left in the same (warehouse, location_type) group --
    a gap in the sequence (1, 3 after deleting 2) is left as-is rather than
    renumbered, since renumbering would change a survivor's
    `generated_code` with nothing else in this system expecting that."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    pending = db.scalar(
        select(Revision).where(
            Revision.entity_type == "location", Revision.entity_id == location_id, Revision.status == "pending"
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This location has a pending revision request -- approve or reject it before deleting.",
        )

    db.delete(location)
    db.commit()
