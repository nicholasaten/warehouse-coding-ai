from pydantic import BaseModel


class WarehouseSummaryRead(BaseModel):
    total_warehouses: int
    active_warehouses: int
    empty_warehouses: int
    underutilized_warehouses: int
    overloaded_warehouses: int
    warehouses_without_capacity_set: int


class LocationSummaryRead(BaseModel):
    total_locations: int
    pending_duplicate_review: int


class DashboardSummaryRead(BaseModel):
    warehouses: WarehouseSummaryRead
    locations: LocationSummaryRead


class WarehouseCapacityRead(BaseModel):
    location_count: int
    capacity: int | None
    occupancy_rate: float | None
    status: str
