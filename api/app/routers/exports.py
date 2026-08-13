import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.services.export_service import export_site_master

# Admin only -- same restriction as /uploads, the format this mirrors.
router = APIRouter(prefix="/exports", tags=["exports"], dependencies=[Depends(require_role("admin"))])


@router.get("/hospital-unit")
def export_hospital_unit(site_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Downloads a Warehouse Master + Location Master .xlsx for one
    Hospital Unit, scoped to its current Warehouses/Locations -- see
    export_service.export_site_master's docstring for why the columns
    exactly match what /uploads already accepts."""
    content, filename = export_site_master(db, site_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
