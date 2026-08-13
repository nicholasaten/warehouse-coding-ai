import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.schemas.config import (
    CategoryRackMappingCreate,
    CategoryRackMappingRead,
    LocationTypeConfigCreate,
    LocationTypeConfigRead,
    SiteCreate,
    SiteRead,
    WarehouseCodeConfigCreate,
    WarehouseCodeConfigRead,
    WarehouseTypeConfigCreate,
    WarehouseTypeConfigRead,
)

# GET endpoints are open to any authenticated role (admin or pic) -- a PIC
# needs to read this reference data too (e.g. location type options) to
# submit a sensible revision request. POST endpoints are admin-only,
# individually gated below: these are the fixed business-rule tables the
# whole system's ID generation reads from, never written to by the rule
# engine, AI, or a PIC.
router = APIRouter(prefix="/config", dependencies=[Depends(get_current_user)])


@router.get("/sites", response_model=list[SiteRead])
def list_sites(db: Session = Depends(get_db)) -> list[Site]:
    return list(db.scalars(select(Site).order_by(Site.code)).all())


@router.post("/sites", response_model=SiteRead, status_code=201, dependencies=[Depends(require_role("admin"))])
def create_site(payload: SiteCreate, db: Session = Depends(get_db)) -> Site:
    site = Site(**payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/warehouse-types", response_model=list[WarehouseTypeConfigRead])
def list_warehouse_types(db: Session = Depends(get_db)) -> list[WarehouseTypeConfig]:
    return list(db.scalars(select(WarehouseTypeConfig).order_by(WarehouseTypeConfig.code)).all())


@router.post(
    "/warehouse-types", response_model=WarehouseTypeConfigRead, status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
def create_warehouse_type(payload: WarehouseTypeConfigCreate, db: Session = Depends(get_db)) -> WarehouseTypeConfig:
    row = WarehouseTypeConfig(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/warehouse-codes", response_model=list[WarehouseCodeConfigRead])
def list_warehouse_codes(
    warehouse_type_code: str | None = None, db: Session = Depends(get_db)
) -> list[WarehouseCodeConfig]:
    query = select(WarehouseCodeConfig).order_by(WarehouseCodeConfig.warehouse_type_code, WarehouseCodeConfig.code)
    if warehouse_type_code:
        query = query.where(WarehouseCodeConfig.warehouse_type_code == warehouse_type_code)
    return list(db.scalars(query).all())


@router.post(
    "/warehouse-codes", response_model=WarehouseCodeConfigRead, status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
def create_warehouse_code(payload: WarehouseCodeConfigCreate, db: Session = Depends(get_db)) -> WarehouseCodeConfig:
    row = WarehouseCodeConfig(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/location-types", response_model=list[LocationTypeConfigRead])
def list_location_types(
    warehouse_type_code: str | None = None, db: Session = Depends(get_db)
) -> list[LocationTypeConfig]:
    query = select(LocationTypeConfig).order_by(LocationTypeConfig.warehouse_type_code, LocationTypeConfig.code)
    if warehouse_type_code:
        query = query.where(LocationTypeConfig.warehouse_type_code == warehouse_type_code)
    return list(db.scalars(query).all())


@router.post(
    "/location-types", response_model=LocationTypeConfigRead, status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
def create_location_type(payload: LocationTypeConfigCreate, db: Session = Depends(get_db)) -> LocationTypeConfig:
    row = LocationTypeConfig(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/category-rack-mappings", response_model=list[CategoryRackMappingRead])
def list_category_rack_mappings(db: Session = Depends(get_db)) -> list[CategoryRackMapping]:
    return list(db.scalars(select(CategoryRackMapping).order_by(CategoryRackMapping.raw_category_text)).all())


@router.post(
    "/category-rack-mappings", response_model=CategoryRackMappingRead, status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
def create_category_rack_mapping(
    payload: CategoryRackMappingCreate, db: Session = Depends(get_db)
) -> CategoryRackMapping:
    row = CategoryRackMapping(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
