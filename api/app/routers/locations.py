import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.location import Location
from app.models.revision import Revision
from app.models.warehouse import Warehouse
from app.schemas.location import LocationCreate, LocationRead, LocationReassignWarehouse, LocationUpdate
from app.services.location_service import create_location, delete_location, reassign_location_warehouse

router = APIRouter(prefix="/locations", tags=["locations"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[LocationRead])
def list_locations(
    warehouse_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    has_pending_revision: bool | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LocationRead]:
    """Backs Admin Monitoring (Review Workflow item #1) -- same filter set
    as warehouses.py's list endpoint, plus warehouse_id since Locations
    nest under a Warehouse."""
    query = select(Location).order_by(Location.generated_code)
    if warehouse_id:
        query = query.where(Location.warehouse_id == warehouse_id)
    if current_user.role == "pic":
        # A Location has no site_id of its own -- scope through its
        # Warehouse, same "never trust a client-passed id" pattern as
        # everywhere else a PIC is restricted to their own Hospital Unit.
        query = query.join(Warehouse, Warehouse.id == Location.warehouse_id).where(
            Warehouse.site_id == current_user.site_id
        )
    elif site_id:
        query = query.join(Warehouse, Warehouse.id == Location.warehouse_id).where(Warehouse.site_id == site_id)
    if is_active is not None:
        query = query.where(Location.is_active == is_active)

    locations = list(db.scalars(query).all())
    pending_ids = set(
        db.scalars(
            select(Revision.entity_id).where(Revision.entity_type == "location", Revision.status == "pending")
        ).all()
    )
    results = []
    for location in locations:
        pending = location.id in pending_ids
        if has_pending_revision is not None and pending != has_pending_revision:
            continue
        item = LocationRead.model_validate(location)
        item.has_pending_revision = pending
        results.append(item)
    return results


@router.post("", response_model=LocationRead, status_code=201, dependencies=[Depends(require_role("admin"))])
def create_location_endpoint(payload: LocationCreate, db: Session = Depends(get_db)) -> Location:
    """Admin only -- see warehouses.py's create endpoint docstring."""
    return create_location(
        db,
        warehouse_id=payload.warehouse_id,
        location_type_code=payload.location_type_code,
        category_rack_raw=payload.category_rack_raw,
        description=payload.description,
    )


@router.get("/{location_id}", response_model=LocationRead)
def get_location(
    location_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> LocationRead:
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    if current_user.role == "pic":
        warehouse = db.get(Warehouse, location.warehouse_id)
        if warehouse is None or warehouse.site_id != current_user.site_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    pending = db.scalar(
        select(Revision.id).where(
            Revision.entity_type == "location", Revision.entity_id == location.id, Revision.status == "pending"
        )
    )
    item = LocationRead.model_validate(location)
    item.has_pending_revision = pending is not None
    return item


@router.patch("/{location_id}", response_model=LocationRead, dependencies=[Depends(require_role("admin"))])
def update_location(location_id: uuid.UUID, payload: LocationUpdate, db: Session = Depends(get_db)) -> Location:
    """Admin's direct-edit path -- see warehouses.py's update_warehouse
    docstring."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    db.commit()
    db.refresh(location)
    return location


@router.post(
    "/{location_id}/reassign-warehouse", response_model=LocationRead, dependencies=[Depends(require_role("admin"))]
)
def reassign_location_warehouse_endpoint(
    location_id: uuid.UUID, payload: LocationReassignWarehouse, db: Session = Depends(get_db)
) -> Location:
    """Moves a Location into a different Warehouse -- see
    location_service.reassign_location_warehouse's docstring. Used e.g. when
    combining two warehouses into one: reassign every Location out of the
    warehouse being retired, then delete it."""
    return reassign_location_warehouse(db, location_id, payload.warehouse_id)


@router.delete("/{location_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_location_endpoint(location_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Hard delete -- see location_service.delete_location's docstring."""
    delete_location(db, location_id)
