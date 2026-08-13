"""Self-tests the upload pipeline against an isolated in-memory SQLite DB,
using synthetic .xlsx files built in-memory (never touches the real
Neon database)."""

import io

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.upload_batch import UploadBatch
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.excel_ingest_service import ingest_location_master, ingest_warehouse_master

import app.models  # noqa: F401


def _xlsx_bytes(headers: list[str], rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def seeded(db):
    from app.models.user import User

    admin = User(full_name="Test Admin", email="admin@test.com", password_hash="x")
    db.add(admin)
    db.add(Site(code="RSUS", name="Rumah Sakit Umum Siloam", short_code="US"))
    db.add(WarehouseTypeConfig(code="A", description="Non-General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="01", description="Pharmacy Mainstore"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.commit()
    return admin


WAREHOUSE_HEADERS = ["Site Code", "Warehouse Type Code", "Warehouse Code", "Warehouse Name", "Description", "Capacity"]
LOCATION_HEADERS = ["Warehouse Code", "Category Rack", "Description"]


def test_warehouse_master_creates_rows(db, seeded):
    content = _xlsx_bytes(
        WAREHOUSE_HEADERS,
        [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""]],
    )
    batch = ingest_warehouse_master(db, seeded.id, "wh.xlsx", content)
    assert batch.status == "completed"
    assert batch.success_count == 1
    assert batch.error_count == 0
    wh = db.scalar(select(Warehouse))
    assert wh.generated_code == "RSUS-A01"  # lone warehouse in its group -- no duplicate letter


def test_warehouse_master_second_distinct_name_triggers_relettering(db, seeded):
    content = _xlsx_bytes(
        WAREHOUSE_HEADERS,
        [
            ["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""],
            ["RSUS", "A", "01", "Pharmacy Mainstore Consumables", "", ""],
        ],
    )
    batch = ingest_warehouse_master(db, seeded.id, "wh.xlsx", content)
    assert batch.success_count == 2
    codes = sorted(w.generated_code for w in db.scalars(select(Warehouse)).all())
    assert codes == ["RSUS-A01A", "RSUS-A01B"]


def test_warehouse_master_reupload_updates_in_place_not_duplicate(db, seeded):
    content = _xlsx_bytes(WAREHOUSE_HEADERS, [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "v1", "10"]])
    ingest_warehouse_master(db, seeded.id, "wh.xlsx", content)

    content2 = _xlsx_bytes(WAREHOUSE_HEADERS, [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "v2", "20"]])
    batch2 = ingest_warehouse_master(db, seeded.id, "wh2.xlsx", content2)

    assert batch2.success_count == 1
    all_warehouses = list(db.scalars(select(Warehouse)).all())
    assert len(all_warehouses) == 1  # updated in place, not a second row
    assert all_warehouses[0].description == "v2"
    assert all_warehouses[0].capacity == 20


def test_warehouse_master_rejects_missing_column(db, seeded):
    content = _xlsx_bytes(["Site Code", "Warehouse Name"], [["RSUS", "Something"]])
    batch = ingest_warehouse_master(db, seeded.id, "wh.xlsx", content)
    assert batch.status == "failed"


def test_warehouse_master_reports_unknown_site(db, seeded):
    content = _xlsx_bytes(WAREHOUSE_HEADERS, [["NOPE", "A", "01", "Something", "", ""]])
    batch = ingest_warehouse_master(db, seeded.id, "wh.xlsx", content)
    assert batch.success_count == 0
    assert batch.error_count == 1


def test_location_master_creates_and_generates_correct_code(db, seeded):
    wh_content = _xlsx_bytes(WAREHOUSE_HEADERS, [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""]])
    ingest_warehouse_master(db, seeded.id, "wh.xlsx", wh_content)

    loc_content = _xlsx_bytes(
        LOCATION_HEADERS,
        [
            ["RSUS-A01", "DRUGS", "DRUGS - PSIKOTROPIKA"],
            ["RSUS-A01", "DRUGS", "DRUGS - OBAT-OBAT TERTENTU"],
        ],
    )
    batch = ingest_location_master(db, seeded.id, "loc.xlsx", loc_content)
    assert batch.success_count == 2
    codes = sorted(loc.generated_code for loc in db.scalars(select(Location)).all())
    assert codes == ["USA01-A01", "USA01-A02"]


def test_location_master_detects_duplicate_description(db, seeded):
    wh_content = _xlsx_bytes(WAREHOUSE_HEADERS, [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""]])
    ingest_warehouse_master(db, seeded.id, "wh.xlsx", wh_content)

    loc_content = _xlsx_bytes(
        LOCATION_HEADERS,
        [
            ["RSUS-A01", "DRUGS", "DRUGS - PSIKOTROPIKA"],
            ["RSUS-A01", "DRUGS", "DRUGS - PSIKOTROPIKA"],  # exact duplicate
        ],
    )
    batch = ingest_location_master(db, seeded.id, "loc.xlsx", loc_content)
    assert batch.success_count == 1
    assert batch.error_count == 1
    assert db.scalar(select(Location).where(Location.description == "DRUGS - PSIKOTROPIKA")) is not None
    assert len(list(db.scalars(select(Location)).all())) == 1


def test_location_master_reports_unmapped_category_rack(db, seeded):
    wh_content = _xlsx_bytes(WAREHOUSE_HEADERS, [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""]])
    ingest_warehouse_master(db, seeded.id, "wh.xlsx", wh_content)

    loc_content = _xlsx_bytes(LOCATION_HEADERS, [["RSUS-A01", "SOME UNKNOWN CATEGORY", "Whatever"]])
    batch = ingest_location_master(db, seeded.id, "loc.xlsx", loc_content)
    assert batch.success_count == 0
    assert batch.error_count == 1


def test_location_master_reports_unknown_warehouse_code(db, seeded):
    loc_content = _xlsx_bytes(LOCATION_HEADERS, [["RSUS-Z99", "DRUGS", "Whatever"]])
    batch = ingest_location_master(db, seeded.id, "loc.xlsx", loc_content)
    assert batch.success_count == 0
    assert batch.error_count == 1
