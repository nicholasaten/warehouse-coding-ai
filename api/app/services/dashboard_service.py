"""Warehouse/Location Summary + Capacity Analysis (Responsibilities #4/#5/#6).

Honest limitation, stated up front: this system tracks the IDENTITY of a
location (its generated code exists or it doesn't) -- it has no inventory/
stock model, so there is no data anywhere about how much physical stock
sits in any given location. "Occupancy" here is therefore a proxy:
`location_count / warehouse.capacity`, i.e. how many distinct storage
locations have been defined for a warehouse versus how many it's sized to
hold. That is a genuinely different measurement from "how full is this
warehouse of actual goods," which the original brief's wording implies but
which nothing in this system can compute without a real inventory feed.

Most of what the brief calls "duplicate/format validation" is prevented
structurally rather than needing an after-the-fact check: generated_code
is always server-computed (see id_generator_service), never accepted as
user input, and duplicate warehouses/locations are blocked at the database
level by unique constraints (see 0001/0002 migrations) plus the upload
pipeline's exact-match and merge-suggestion checks (see
excel_ingest_service / merge_suggestion_service). The one genuinely
after-the-fact-only signal is a warehouse with zero locations, which is
what `empty_warehouses` below actually means.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.merge_suggestion import MergeSuggestion
from app.models.warehouse import Warehouse

UNDERUTILIZED_THRESHOLD = 0.30
OVERLOADED_THRESHOLD = 1.0  # more locations than capacity


def _occupancy_status(location_count: int, capacity: int | None) -> str:
    if location_count == 0:
        return "empty"
    if capacity is None:
        return "no_capacity_set"
    rate = location_count / capacity
    if rate > OVERLOADED_THRESHOLD:
        return "overloaded"
    if rate < UNDERUTILIZED_THRESHOLD:
        return "underutilized"
    return "normal"


def warehouse_summary(db: Session, site_id: uuid.UUID | None = None) -> dict:
    query = select(Warehouse)
    if site_id is not None:
        query = query.where(Warehouse.site_id == site_id)
    warehouses = list(db.scalars(query).all())
    counts = dict(
        db.execute(
            select(Location.warehouse_id, func.count(Location.id)).group_by(Location.warehouse_id)
        ).all()
    )

    total = len(warehouses)
    active = sum(1 for w in warehouses if w.is_active)
    empty = underutilized = overloaded = no_capacity_set = 0

    for w in warehouses:
        location_count = counts.get(w.id, 0)
        status = _occupancy_status(location_count, w.capacity)
        if status == "empty":
            empty += 1
        elif status == "underutilized":
            underutilized += 1
        elif status == "overloaded":
            overloaded += 1
        elif status == "no_capacity_set":
            no_capacity_set += 1

    return {
        "total_warehouses": total,
        "active_warehouses": active,
        "empty_warehouses": empty,
        "underutilized_warehouses": underutilized,
        "overloaded_warehouses": overloaded,
        "warehouses_without_capacity_set": no_capacity_set,
    }


def location_summary(db: Session, site_id: uuid.UUID | None = None) -> dict:
    loc_query = select(func.count(Location.id))
    merge_query = select(func.count(MergeSuggestion.id)).where(MergeSuggestion.status == "pending")
    if site_id is not None:
        loc_query = loc_query.join(Warehouse, Warehouse.id == Location.warehouse_id).where(
            Warehouse.site_id == site_id
        )
        merge_query = merge_query.join(Warehouse, Warehouse.id == MergeSuggestion.warehouse_id).where(
            Warehouse.site_id == site_id
        )

    total_locations = db.scalar(loc_query) or 0
    pending_merge_suggestions = db.scalar(merge_query) or 0

    return {
        "total_locations": total_locations,
        # "Duplicate Locations" per the brief -- these are near-duplicates
        # already caught and held for review, not yet resolved either way.
        "pending_duplicate_review": pending_merge_suggestions,
    }


def warehouse_capacity_detail(db: Session, warehouse: Warehouse) -> dict:
    location_count = db.scalar(select(func.count(Location.id)).where(Location.warehouse_id == warehouse.id)) or 0
    status = _occupancy_status(location_count, warehouse.capacity)
    occupancy_rate = (location_count / warehouse.capacity) if warehouse.capacity else None
    return {
        "location_count": location_count,
        "capacity": warehouse.capacity,
        "occupancy_rate": occupancy_rate,
        "status": status,
    }
