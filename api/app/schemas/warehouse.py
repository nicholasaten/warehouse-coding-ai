import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field


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
    pic_acknowledged_at: datetime | None
    pic_acknowledged_by: uuid.UUID | None

    @computed_field
    @property
    def needs_pic_review(self) -> bool:
        """Derived straight from pic_acknowledged_at, unlike
        has_pending_revision -- that one needs a separate Revision query
        per endpoint, this one doesn't, so it's always correct here
        without every route having to remember to set it."""
        return self.pic_acknowledged_at is None

    class Config:
        from_attributes = True
