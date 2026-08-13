import uuid
from datetime import datetime

from pydantic import BaseModel


class LocationCreate(BaseModel):
    warehouse_id: uuid.UUID
    location_type_code: str
    category_rack_raw: str | None = None
    description: str


class LocationReassignWarehouse(BaseModel):
    warehouse_id: uuid.UUID


class LocationLayoutUpdate(BaseModel):
    layout_x: float
    layout_y: float
    layout_width: float
    layout_height: float


class LocationUpdate(BaseModel):
    """Admin-only direct edit -- see WarehouseUpdate's docstring."""

    description: str | None = None
    category_rack_raw: str | None = None
    is_active: bool | None = None


class LocationRead(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    location_type_code: str
    seq: int
    generated_code: str
    category_rack_raw: str | None
    description: str
    is_active: bool
    created_at: datetime
    has_pending_revision: bool = False
    layout_x: float | None
    layout_y: float | None
    layout_width: float | None
    layout_height: float | None

    class Config:
        from_attributes = True
