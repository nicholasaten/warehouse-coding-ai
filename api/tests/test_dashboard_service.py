import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.dashboard_service import location_summary, warehouse_capacity_detail, warehouse_summary
from app.services.location_service import create_location
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
    for code in ("01", "02", "03", "04"):
        db.add(WarehouseCodeConfig(warehouse_type_code="A", code=code, description=f"WH {code}"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.commit()
    return site


def test_empty_warehouse_counted_correctly(db, seeded):
    create_warehouse(db, seeded.id, "A", "01", "Empty WH", None, capacity=10)
    summary = warehouse_summary(db)
    assert summary["total_warehouses"] == 1
    assert summary["empty_warehouses"] == 1
    assert summary["underutilized_warehouses"] == 0
    assert summary["overloaded_warehouses"] == 0


def test_underutilized_warehouse(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "02", "Underutilized WH", None, capacity=10)
    create_location(db, wh.id, "A", "DRUGS", "Only One Location")  # 1/10 = 10% < 30% threshold
    summary = warehouse_summary(db)
    assert summary["underutilized_warehouses"] == 1
    assert summary["overloaded_warehouses"] == 0
    assert summary["empty_warehouses"] == 0


def test_overloaded_warehouse(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "03", "Overloaded WH", None, capacity=2)
    create_location(db, wh.id, "A", "DRUGS", "Loc 1")
    create_location(db, wh.id, "A", "DRUGS", "Loc 2")
    create_location(db, wh.id, "A", "DRUGS", "Loc 3")  # 3/2 = 150% > 100% threshold
    summary = warehouse_summary(db)
    assert summary["overloaded_warehouses"] == 1


def test_normal_warehouse_and_no_capacity_set(db, seeded):
    wh_normal = create_warehouse(db, seeded.id, "A", "04", "Normal WH", None, capacity=2)
    create_location(db, wh_normal.id, "A", "DRUGS", "Loc 1")  # 1/2 = 50%, within 30-100% band

    wh_no_cap = create_warehouse(db, seeded.id, "A", "01", "No Capacity WH -- dup group", None, capacity=None)
    create_location(db, wh_no_cap.id, "A", "DRUGS", "Loc A")

    summary = warehouse_summary(db)
    assert summary["underutilized_warehouses"] == 0
    assert summary["overloaded_warehouses"] == 0
    assert summary["warehouses_without_capacity_set"] == 1


def test_location_summary_counts_total_and_pending(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "WH", None, capacity=10)
    create_location(db, wh.id, "A", "DRUGS", "DRUGS - TABLET")
    summary = location_summary(db)
    assert summary["total_locations"] == 1
    assert summary["pending_duplicate_review"] == 0


def test_warehouse_capacity_detail_shape(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "WH", None, capacity=4)
    create_location(db, wh.id, "A", "DRUGS", "Loc 1")
    detail = warehouse_capacity_detail(db, wh)
    assert detail["location_count"] == 1
    assert detail["capacity"] == 4
    assert detail["occupancy_rate"] == 0.25
    assert detail["status"] == "underutilized"  # 25% < 30% threshold
