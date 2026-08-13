import uuid
from datetime import datetime

from pydantic import BaseModel


class WarehouseCreate(BaseModel):
    site_id: uuid.UUID
    warehouse_type_code: str
    warehouse_code: str
    name: str
    description: str | None = None
    capacity: int | None = None


class WarehouseMerge(BaseModel):
    target_warehouse_id: uuid.UUID


class WarehouseUpdate(BaseModel):
    """Admin-only direct edit (see routers/warehouses.py PATCH) -- same
    descriptive-fields-only scope as the PIC revision workflow, plus
    is_active since toggling a warehouse's status is an Admin-only power
    that was never meant to go through a revision request."""

    name: str | None = None
    description: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class WarehouseRead(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    warehouse_type_code: str
    warehouse_code: str
    duplicate_letter: str | None
    generated_code: str
    name: str
    description: str | None
    capacity: int | None
    is_active: bool
    created_at: datetime
    has_pending_revision: bool = False

    class Config:
        from_attributes = True
