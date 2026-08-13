import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.revision import Revision
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseMerge, WarehouseRead, WarehouseUpdate
from app.services.warehouse_service import create_warehouse, delete_warehouse, merge_warehouse

router = APIRouter(prefix="/warehouses", tags=["warehouses"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    site_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    has_pending_revision: bool | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WarehouseRead]:
    """Backs Admin Monitoring (Review Workflow item #1): filter by Hospital
    Code (site_id), status (is_active), and revision status
    (has_pending_revision, computed below -- Warehouse has no such column
    of its own)."""
    query = select(Warehouse).order_by(Warehouse.generated_code)
    if current_user.role == "pic":
        # A PIC can only ever see their own Hospital Unit's warehouses --
        # any site_id they pass is overridden here, never trusted from the
        # query string, same pattern as the sibling readiness-tracker app.
        query = query.where(Warehouse.site_id == current_user.site_id)
    elif site_id:
        query = query.where(Warehouse.site_id == site_id)
    if is_active is not None:
        query = query.where(Warehouse.is_active == is_active)

    warehouses = list(db.scalars(query).all())
    pending_ids = set(
        db.scalars(
            select(Revision.entity_id).where(Revision.entity_type == "warehouse", Revision.status == "pending")
        ).all()
    )
    results = []
    for warehouse in warehouses:
        pending = warehouse.id in pending_ids
        if has_pending_revision is not None and pending != has_pending_revision:
            continue
        item = WarehouseRead.model_validate(warehouse)
        item.has_pending_revision = pending
        results.append(item)
    return results


@router.post("", response_model=WarehouseRead, status_code=201, dependencies=[Depends(require_role("admin"))])
def create_warehouse_endpoint(payload: WarehouseCreate, db: Session = Depends(get_db)) -> Warehouse:
    """Admin only -- PICs can never create or edit a warehouse directly;
    their only path to changing anything is a revision request (see
    app/routers/revisions.py)."""
    return create_warehouse(
        db,
        site_id=payload.site_id,
        warehouse_type_code=payload.warehouse_type_code,
        warehouse_code=payload.warehouse_code,
        name=payload.name,
        description=payload.description,
        capacity=payload.capacity,
    )


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> WarehouseRead:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if current_user.role == "pic" and warehouse.site_id != current_user.site_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    pending = db.scalar(
        select(Revision.id).where(
            Revision.entity_type == "warehouse", Revision.entity_id == warehouse.id, Revision.status == "pending"
        )
    )
    item = WarehouseRead.model_validate(warehouse)
    item.has_pending_revision = pending is not None
    return item


@router.patch("/{warehouse_id}", response_model=WarehouseRead, dependencies=[Depends(require_role("admin"))])
def update_warehouse(warehouse_id: uuid.UUID, payload: WarehouseUpdate, db: Session = Depends(get_db)) -> Warehouse:
    """Admin's direct-edit path (Review Workflow item #1) -- distinct from
    the PIC revision workflow in app/routers/revisions.py, which never
    writes here itself. Only descriptive fields + is_active; the
    formula-driving fields (site_id, type/code, duplicate_letter,
    generated_code) are never editable post-creation."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.post(
    "/{warehouse_id}/merge-into", response_model=WarehouseRead, dependencies=[Depends(require_role("admin"))]
)
def merge_warehouse_endpoint(
    warehouse_id: uuid.UUID, payload: WarehouseMerge, db: Session = Depends(get_db)
) -> Warehouse:
    """Merges this warehouse into an existing one -- see
    warehouse_service.merge_warehouse's docstring. Moves every Location out
    (recoded under the target), then deletes this warehouse; it never
    shows up in the list again afterward."""
    return merge_warehouse(db, warehouse_id, payload.target_warehouse_id)


@router.delete("/{warehouse_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_warehouse_endpoint(warehouse_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Hard delete -- see warehouse_service.delete_warehouse's docstring
    for what cascades (Locations, MergeSuggestions), what survives with a
    nulled reference (raw-import suggestion audit rows), and what blocks
    it (a still-pending Revision)."""
    delete_warehouse(db, warehouse_id)
