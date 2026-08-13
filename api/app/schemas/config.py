import uuid

from pydantic import BaseModel


class SiteCreate(BaseModel):
    code: str
    name: str
    short_code: str


class SiteRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    short_code: str
    is_active: bool

    class Config:
        from_attributes = True


class WarehouseTypeConfigCreate(BaseModel):
    code: str
    description: str


class WarehouseTypeConfigRead(BaseModel):
    id: uuid.UUID
    code: str
    description: str

    class Config:
        from_attributes = True


class WarehouseCodeConfigCreate(BaseModel):
    warehouse_type_code: str
    code: str
    description: str


class WarehouseCodeConfigRead(BaseModel):
    id: uuid.UUID
    warehouse_type_code: str
    code: str
    description: str

    class Config:
        from_attributes = True


class LocationTypeConfigCreate(BaseModel):
    warehouse_type_code: str
    code: str
    description: str
    is_whole_warehouse: bool = False


class LocationTypeConfigRead(BaseModel):
    id: uuid.UUID
    warehouse_type_code: str
    code: str
    description: str
    is_whole_warehouse: bool

    class Config:
        from_attributes = True


class CategoryRackMappingCreate(BaseModel):
    warehouse_type_code: str
    raw_category_text: str
    location_type_config_id: uuid.UUID


class CategoryRackMappingRead(BaseModel):
    id: uuid.UUID
    warehouse_type_code: str
    raw_category_text: str
    location_type_config_id: uuid.UUID

    class Config:
        from_attributes = True
