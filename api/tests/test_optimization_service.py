import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.location_service import create_location
from app.services.optimization_service import (
    find_merge_candidates,
    find_overloaded_warehouses,
    find_redundant_warehouses,
    find_underutilized_warehouses,
)
from app.services.warehouse_service import create_warehouse

import app.models  # noqa: F401


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def seeded(db):
    site = Site(code="RSUS", name="Rumah Sakit Umum Siloam", short_code="US")
    db.add(site)
    db.add(WarehouseTypeConfig(code="A", description="Non-General Items"))
    for code in ("01", "02", "03", "04", "05"):
        db.add(WarehouseCodeConfig(warehouse_type_code="A", code=code, description=f"WH {code}"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.commit()
    return site


def test_two_underutilized_same_type_warehouses_are_a_merge_candidate(db, seeded):
    a = create_warehouse(db, seeded.id, "A", "01", "Warehouse A", None, capacity=10)
    b = create_warehouse(db, seeded.id, "A", "02", "Warehouse B", None, capacity=10)
    create_location(db, a.id, "A", "DRUGS", "Loc A1")  # 1/10 = 10%, underutilized
    create_location(db, b.id, "A", "DRUGS", "Loc B1")  # 1/10 = 10%, underutilized

    candidates = find_merge_candidates(db)
    assert len(candidates) == 1
    ids = {candidates[0].warehouse_a.id, candidates[0].warehouse_b.id}
    assert ids == {a.id, b.id}


def test_full_warehouses_are_not_merge_candidates(db, seeded):
    a = create_warehouse(db, seeded.id, "A", "01", "Full A", None, capacity=1)
    b = create_warehouse(db, seeded.id, "A", "02", "Full B", None, capacity=1)
    create_location(db, a.id, "A", "DRUGS", "Loc A1")  # 100% -- not underutilized
    create_location(db, b.id, "A", "DRUGS", "Loc B1")
    assert find_merge_candidates(db) == []


def test_combined_locations_fitting_into_either_is_a_candidate(db, seeded):
    a = create_warehouse(db, seeded.id, "A", "01", "A", None, capacity=20)
    b = create_warehouse(db, seeded.id, "A", "02", "B", None, capacity=20)
    for i in range(5):
        create_location(db, a.id, "A", "DRUGS", f"A Loc {i}")  # 5/20 = 25% < 30%, underutilized
        create_location(db, b.id, "A", "DRUGS", f"B Loc {i}")  # same
    # combined = 10, fits into either 20-capacity warehouse -> should be a candidate
    assert len(find_merge_candidates(db)) == 1


def test_no_capacity_set_never_counts_as_room(db, seeded):
    # An underutilized-by-location-count warehouse with NO capacity set at
    # all should never be treated as having "room" for a merge -- unknown
    # capacity is not the same as unlimited capacity.
    a = create_warehouse(db, seeded.id, "A", "01", "A", None, capacity=None)
    b = create_warehouse(db, seeded.id, "A", "02", "B", None, capacity=None)
    create_location(db, a.id, "A", "DRUGS", "A Loc 1")
    create_location(db, b.id, "A", "DRUGS", "B Loc 1")
    # Both status "no_capacity_set", not "underutilized" or "empty" --
    # excluded by the status check before capacity/fit is even considered.
    assert find_merge_candidates(db) == []


def test_redundant_underutilized_overloaded_buckets(db, seeded):
    empty = create_warehouse(db, seeded.id, "A", "01", "Empty", None, capacity=10)
    underutil = create_warehouse(db, seeded.id, "A", "02", "Under", None, capacity=10)
    create_location(db, underutil.id, "A", "DRUGS", "Loc")
    overloaded = create_warehouse(db, seeded.id, "A", "03", "Over", None, capacity=1)
    create_location(db, overloaded.id, "A", "DRUGS", "Loc 1")
    create_location(db, overloaded.id, "A", "DRUGS", "Loc 2")

    redundant = find_redundant_warehouses(db)
    assert [w.id for w in redundant] == [empty.id]

    under = find_underutilized_warehouses(db)
    assert [w.id for w in under] == [underutil.id]

    over = find_overloaded_warehouses(db)
    assert [w.id for w in over] == [overloaded.id]


def test_different_warehouse_type_never_a_merge_candidate(db, seeded):
    db.add(WarehouseTypeConfig(code="B", description="General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="B", code="01", description="General WH"))
    db.commit()

    a = create_warehouse(db, seeded.id, "A", "04", "Non-General A", None, capacity=10)
    b = create_warehouse(db, seeded.id, "B", "01", "General B", None, capacity=10)
    create_location(db, a.id, "A", "DRUGS", "Loc A")
    assert find_merge_candidates(db) == []
