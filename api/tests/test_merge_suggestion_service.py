"""Verifies the suggest-only merge-detection layer: a near-duplicate
description is held for review, never auto-created and never silently
dropped; approve leaves the DB as-is, reject creates the real Location."""

import io

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.merge_suggestion import MergeSuggestion
from app.models.site import Site
from app.models.upload_batch import UploadBatch
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.excel_ingest_service import ingest_location_master, ingest_warehouse_master
from app.services.merge_suggestion_service import approve_suggestion, find_similar_location, reject_suggestion

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
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.commit()

    wh_content = _xlsx_bytes(
        ["Site Code", "Warehouse Type Code", "Warehouse Code", "Warehouse Name", "Description", "Capacity"],
        [["RSUS", "A", "01", "Pharmacy Mainstore Drugs", "", ""]],
    )
    ingest_warehouse_master(db, admin.id, "wh.xlsx", wh_content)

    loc_content = _xlsx_bytes(
        ["Warehouse Code", "Category Rack", "Description"], [["RSUS-A01", "DRUGS", "DRUGS - TABLET"]]
    )
    ingest_location_master(db, admin.id, "loc.xlsx", loc_content)
    return admin


def test_near_duplicate_creates_pending_suggestion_not_a_new_location(db, seeded):
    content = _xlsx_bytes(
        ["Warehouse Code", "Category Rack", "Description"], [["RSUS-A01", "DRUGS", "DRUGS - TABLETS"]]  # near-dup
    )
    batch = ingest_location_master(db, seeded.id, "loc2.xlsx", content)

    assert batch.success_count == 0
    assert batch.pending_count == 1
    assert batch.error_count == 0
    assert len(list(db.scalars(select(Location)).all())) == 1  # still just the original
    suggestion = db.scalar(select(MergeSuggestion))
    assert suggestion.status == "pending"
    assert suggestion.raw_description == "DRUGS - TABLETS"
    assert suggestion.similarity_score > 0.9
    assert "DRUGS - TABLET" in suggestion.reasoning


def test_genuinely_different_description_creates_a_new_location_normally(db, seeded):
    content = _xlsx_bytes(
        ["Warehouse Code", "Category Rack", "Description"], [["RSUS-A01", "DRUGS", "DRUGS - INJEKSI"]]
    )
    batch = ingest_location_master(db, seeded.id, "loc2.xlsx", content)

    assert batch.success_count == 1
    assert batch.pending_count == 0
    assert len(list(db.scalars(select(Location)).all())) == 2


def test_approve_suggestion_creates_no_new_location(db, seeded):
    content = _xlsx_bytes(
        ["Warehouse Code", "Category Rack", "Description"], [["RSUS-A01", "DRUGS", "DRUGS - TABLETS"]]
    )
    ingest_location_master(db, seeded.id, "loc2.xlsx", content)
    suggestion = db.scalar(select(MergeSuggestion))

    approve_suggestion(db, suggestion.id)

    db.refresh(suggestion)
    assert suggestion.status == "approved"
    assert suggestion.resolved_at is not None
    assert len(list(db.scalars(select(Location)).all())) == 1  # unchanged


def test_reject_suggestion_creates_the_real_location(db, seeded):
    content = _xlsx_bytes(
        ["Warehouse Code", "Category Rack", "Description"], [["RSUS-A01", "DRUGS", "DRUGS - TABLETS"]]
    )
    ingest_location_master(db, seeded.id, "loc2.xlsx", content)
    suggestion = db.scalar(select(MergeSuggestion))

    new_location = reject_suggestion(db, suggestion.id)

    db.refresh(suggestion)
    assert suggestion.status == "rejected"
    assert new_location.description == "DRUGS - TABLETS"
    assert new_location.generated_code == "USA01-A02"  # second distinct location in this group
    assert len(list(db.scalars(select(Location)).all())) == 2


def test_find_similar_location_scoped_to_warehouse_and_loc_type(db, seeded):
    warehouse = db.scalar(select(Warehouse))
    match, score = find_similar_location(db, warehouse.id, "A", "DRUGS - TABLETS")
    assert match is not None
    assert match.description == "DRUGS - TABLET"
    assert score > 0.9

    no_match, no_score = find_similar_location(db, warehouse.id, "A", "COMPLETELY UNRELATED TEXT HERE")
    assert no_match is None
    assert no_score == 0.0
