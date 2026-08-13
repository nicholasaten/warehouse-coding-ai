"""Deterministic candidate-finding for optimization recommendations (AI
Responsibilities #7/#8) -- everything in this module is plain SQL/Python,
no LLM call. `ai_recommendation_service` takes whatever this module finds
and writes the natural-language explanation for it, once, in a single
batched call -- never per-candidate.

Same honest limitation as dashboard_service: "occupancy" is location count
vs. warehouse.capacity, not actual inventory fullness (no stock model
exists in this system).
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.warehouse import Warehouse
from app.services.dashboard_service import _occupancy_status


@dataclass
class MergeCandidate:
    warehouse_a: Warehouse
    warehouse_b: Warehouse
    location_count_a: int
    location_count_b: int


def _location_counts(db: Session) -> dict:
    return dict(
        db.execute(select(Location.warehouse_id, func.count(Location.id)).group_by(Location.warehouse_id)).all()
    )


def find_merge_candidates(db: Session) -> list[MergeCandidate]:
    """A pair is a merge candidate when: same site, same warehouse_type_code
    (merging across types would violate the fixed formula's own meaning),
    both active, both underutilized or empty, and consolidating one into
    the other wouldn't overload the receiving warehouse's own capacity (if
    set) -- matches the brief's own worked example almost exactly (two
    warehouses of "similar inventory characteristics" with "sufficient
    available capacity")."""
    warehouses = list(db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True))).all())
    counts = _location_counts(db)

    groups: dict[tuple, list[Warehouse]] = {}
    for w in warehouses:
        key = (w.site_id, w.warehouse_type_code)
        groups.setdefault(key, []).append(w)

    candidates: list[MergeCandidate] = []
    for group in groups.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                count_a, count_b = counts.get(a.id, 0), counts.get(b.id, 0)
                status_a = _occupancy_status(count_a, a.capacity)
                status_b = _occupancy_status(count_b, b.capacity)
                if status_a not in ("empty", "underutilized") or status_b not in ("empty", "underutilized"):
                    continue
                # Would B's locations fit inside A's remaining capacity (or
                # vice versa)? Only a real candidate if at least one
                # direction has room -- an unset capacity is treated as
                # "unknown," not "unlimited," so it doesn't count as room.
                fits_into_a = a.capacity is not None and (count_a + count_b) <= a.capacity
                fits_into_b = b.capacity is not None and (count_a + count_b) <= b.capacity
                if fits_into_a or fits_into_b:
                    candidates.append(MergeCandidate(a, b, count_a, count_b))
    return candidates


def find_redundant_warehouses(db: Session) -> list[Warehouse]:
    """Active warehouses with zero locations -- nothing has ever been
    assigned to them, a real candidate for removal or repurposing."""
    counts = _location_counts(db)
    warehouses = list(db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True))).all())
    return [w for w in warehouses if counts.get(w.id, 0) == 0]


def find_underutilized_warehouses(db: Session) -> list[Warehouse]:
    counts = _location_counts(db)
    warehouses = list(db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True))).all())
    return [
        w
        for w in warehouses
        if counts.get(w.id, 0) > 0 and _occupancy_status(counts.get(w.id, 0), w.capacity) == "underutilized"
    ]


def find_overloaded_warehouses(db: Session) -> list[Warehouse]:
    counts = _location_counts(db)
    warehouses = list(db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True))).all())
    return [w for w in warehouses if _occupancy_status(counts.get(w.id, 0), w.capacity) == "overloaded"]
