import uuid
from datetime import datetime

from pydantic import BaseModel


class RawImportBatchRead(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    file_name: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RawRackRow(BaseModel):
    code_rack: str | None
    description: str
    is_active: bool


class RawWarehouseSuggestionRead(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    legacy_code: str
    legacy_name: str
    consolidated_legacy_names: list[str]
    raw_rows: list[RawRackRow]
    suggested_warehouse_type_code: str | None
    suggested_warehouse_code: str | None
    reasoning: str | None
    status: str
    created_warehouse_id: uuid.UUID | None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class RawWarehouseSuggestionApprove(BaseModel):
    warehouse_type_code: str | None = None
    warehouse_code: str | None = None
    name: str | None = None
    description: str | None = None
    capacity: int | None = None


class RawLocationSuggestionRead(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    warehouse_suggestion_id: uuid.UUID
    warehouse_id: uuid.UUID
    legacy_code: str | None
    legacy_description: str
    is_active_raw: bool
    suggested_category_rack: str | None
    reasoning: str | None
    status: str
    created_location_id: uuid.UUID | None
    created_merge_suggestion_id: uuid.UUID | None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class RawLocationSuggestionApprove(BaseModel):
    category_rack: str | None = None
    description: str | None = None
