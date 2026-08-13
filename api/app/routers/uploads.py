import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.upload_batch import UploadBatch
from app.models.upload_error import UploadError
from app.schemas.upload import UploadBatchRead, UploadErrorRead
from app.services.excel_ingest_service import ingest_location_master, ingest_warehouse_master

# Admin only -- bulk-creating warehouses/locations is a master-data
# operation, same restriction as the direct create endpoints.
router = APIRouter(prefix="/uploads", tags=["uploads"], dependencies=[Depends(require_role("admin"))])


@router.post("/warehouse-master", response_model=UploadBatchRead)
async def upload_warehouse_master(
    file: UploadFile, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> UploadBatch:
    content = await file.read()
    return ingest_warehouse_master(db, current_user.id, file.filename or "upload.xlsx", content)


@router.post("/location-master", response_model=UploadBatchRead)
async def upload_location_master(
    file: UploadFile, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> UploadBatch:
    content = await file.read()
    return ingest_location_master(db, current_user.id, file.filename or "upload.xlsx", content)


@router.get("", response_model=list[UploadBatchRead])
def list_uploads(db: Session = Depends(get_db)) -> list[UploadBatch]:
    return list(db.scalars(select(UploadBatch).order_by(UploadBatch.uploaded_at.desc())).all())


@router.get("/{batch_id}/errors", response_model=list[UploadErrorRead])
def list_upload_errors(batch_id: uuid.UUID, db: Session = Depends(get_db)) -> list[UploadError]:
    return list(db.scalars(select(UploadError).where(UploadError.batch_id == batch_id).order_by(UploadError.row_number)).all())
