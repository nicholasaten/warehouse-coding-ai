import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.warehouse import Warehouse
from app.schemas.dashboard import DashboardSummaryRead, WarehouseCapacityRead
from app.services.dashboard_service import location_summary, warehouse_capacity_detail, warehouse_summary

router = APIRouter(tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get(
    "/dashboard/summary", response_model=DashboardSummaryRead, dependencies=[Depends(require_role("admin"))]
)
def get_dashboard_summary(db: Session = Depends(get_db)) -> dict:
    """System-wide -- admin only. A per-site version for PICs isn't built
    yet; not part of what was asked for in the review-workflow request."""
    return {"warehouses": warehouse_summary(db), "locations": location_summary(db)}


@router.get("/warehouses/{warehouse_id}/capacity", response_model=WarehouseCapacityRead)
def get_warehouse_capacity(
    warehouse_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if current_user.role == "pic" and warehouse.site_id != current_user.site_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    return warehouse_capacity_detail(db, warehouse)
