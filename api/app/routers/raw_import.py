import uuid

from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.raw_import import RawImportBatch, RawLocationSuggestion, RawWarehouseSuggestion
from app.schemas.raw_import import (
    RawImportBatchRead,
    RawLocationSuggestionApprove,
    RawLocationSuggestionRead,
    RawWarehouseSuggestionApprove,
    RawWarehouseSuggestionRead,
)
from app.services.raw_import_service import (
    approve_location_suggestion,
    approve_warehouse_suggestion,
    generate_location_suggestions,
    reject_location_suggestion,
    reject_warehouse_suggestion,
    upload_raw_import,
)

# Admin only -- same restriction as /uploads and every other master-data
# creation path; a PIC never touches this.
router = APIRouter(prefix="/raw-import", tags=["raw-import"], dependencies=[Depends(require_role("admin"))])


@router.post("/upload", response_model=RawImportBatchRead, status_code=201)
async def upload(
    file: UploadFile,
    site_id: uuid.UUID = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RawImportBatch:
    content = await file.read()
    batch, _suggestions = upload_raw_import(db, current_user.id, site_id, file.filename or "raw-import.xlsx", content)
    return batch


@router.get("/batches", response_model=list[RawImportBatchRead])
def list_batches(db: Session = Depends(get_db)) -> list[RawImportBatch]:
    return list(db.scalars(select(RawImportBatch).order_by(RawImportBatch.uploaded_at.desc())).all())


@router.get("/batches/{batch_id}/warehouses", response_model=list[RawWarehouseSuggestionRead])
def list_warehouse_suggestions(
    batch_id: uuid.UUID, status: str | None = None, db: Session = Depends(get_db)
) -> list[RawWarehouseSuggestion]:
    query = select(RawWarehouseSuggestion).where(RawWarehouseSuggestion.batch_id == batch_id)
    if status:
        query = query.where(RawWarehouseSuggestion.status == status)
    return list(db.scalars(query.order_by(RawWarehouseSuggestion.legacy_name)).all())


@router.post("/warehouses/{suggestion_id}/approve", response_model=RawWarehouseSuggestionRead)
def approve_warehouse(
    suggestion_id: uuid.UUID, payload: RawWarehouseSuggestionApprove, db: Session = Depends(get_db)
) -> RawWarehouseSuggestion:
    """Applies the AI's suggestion as-is, or an admin override supplied
    here -- either way this goes through create_warehouse(), the exact same
    path a manual or file-upload warehouse creation uses."""
    return approve_warehouse_suggestion(
        db,
        suggestion_id,
        warehouse_type_code=payload.warehouse_type_code,
        warehouse_code=payload.warehouse_code,
        name=payload.name,
        description=payload.description,
        capacity=payload.capacity,
    )


@router.post("/warehouses/{suggestion_id}/reject", response_model=RawWarehouseSuggestionRead)
def reject_warehouse(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> RawWarehouseSuggestion:
    return reject_warehouse_suggestion(db, suggestion_id)


@router.post("/batches/{batch_id}/locations/suggest", response_model=list[RawLocationSuggestionRead])
def suggest_locations(batch_id: uuid.UUID, db: Session = Depends(get_db)) -> list[RawLocationSuggestion]:
    """One batched Groq call covering every approved warehouse's racks that
    doesn't already have location suggestions -- safe to call again after
    approving more warehouses, it only covers what's new."""
    return generate_location_suggestions(db, batch_id)


@router.get("/batches/{batch_id}/locations", response_model=list[RawLocationSuggestionRead])
def list_location_suggestions(
    batch_id: uuid.UUID, status: str | None = None, db: Session = Depends(get_db)
) -> list[RawLocationSuggestion]:
    query = select(RawLocationSuggestion).where(RawLocationSuggestion.batch_id == batch_id)
    if status:
        query = query.where(RawLocationSuggestion.status == status)
    return list(db.scalars(query.order_by(RawLocationSuggestion.legacy_description)).all())


@router.post("/locations/{suggestion_id}/approve", response_model=RawLocationSuggestionRead)
def approve_location(
    suggestion_id: uuid.UUID, payload: RawLocationSuggestionApprove, db: Session = Depends(get_db)
) -> RawLocationSuggestion:
    """May create a real Location, or -- if it turns out to be textually
    similar to one that already exists -- a MergeSuggestion instead, exactly
    like a normal Location Master upload would."""
    return approve_location_suggestion(db, suggestion_id, category_rack=payload.category_rack, description=payload.description)


@router.post("/locations/{suggestion_id}/reject", response_model=RawLocationSuggestionRead)
def reject_location(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> RawLocationSuggestion:
    return reject_location_suggestion(db, suggestion_id)
