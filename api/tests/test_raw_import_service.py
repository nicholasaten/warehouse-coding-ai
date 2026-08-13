"""Tests the AI-assisted raw-import mapping feature against an isolated
in-memory SQLite DB, using synthetic raw-format .xlsx files built in-memory.
Deliberately forces `settings.groq_api_key` to None for every test here
(via monkeypatch) so these always exercise the deterministic fallback path
(no AI suggestion, admin must supply one) regardless of whatever real key a
developer's local .env has -- same reasoning and pattern as
test_ai_recommendation_service.py's `_no_groq_key` fixture."""

import io

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.merge_suggestion import MergeSuggestion
from app.models.raw_import import RawImportBatch, RawLocationSuggestion, RawWarehouseSuggestion
from app.models.site import Site
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.location_service import create_location
from app.services.raw_import_service import (
    _build_clustered_candidates,
    approve_location_suggestion,
    approve_warehouse_suggestion,
    confirmed_location_examples,
    confirmed_warehouse_examples,
    generate_location_suggestions,
    reject_location_suggestion,
    reject_warehouse_suggestion,
    upload_raw_import,
)
from fastapi import HTTPException

import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def _no_groq_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)


def _raw_xlsx_bytes(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Organization", "CodeStore", "Store", "CodeStoreRack", "StoreRack", "ActiveStoreRack"])
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
    site = Site(code="RSUS", name="Rumah Sakit Umum Siloam", short_code="US")
    db.add(site)
    db.add(WarehouseTypeConfig(code="A", description="Non-General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="01", description="Pharmacy Mainstore"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="08", description="Emergency"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="CONSUMABLES", location_type_config_id=drugs.id))
    db.commit()
    return {"admin": admin, "site": site}


RAW_ROWS = [
    ["RUMAH SAKIT UMUM SILOAM", "RSUS-1", "PHARMACY MAINSTORE DRUGS", "PHAMSP10", "DRUGS - RAK 1", 1],
    ["RUMAH SAKIT UMUM SILOAM", "RSUS-1", "PHARMACY MAINSTORE DRUGS", "PHAMSP20", "DRUGS - RAK 2", 1],
    ["RUMAH SAKIT UMUM SILOAM", "RSUS-25", "EMERGENCY", "USA08-A06", "CONSUMABLES - LEMARI A", 1],
    ["RUMAH SAKIT UMUM SILOAM", "RSUS-25", "EMERGENCY", "ETCLB", "LEMARI B", 0],
]


def test_upload_parses_and_groups_by_store(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)

    assert isinstance(batch, RawImportBatch)
    assert len(suggestions) == 2  # two distinct (CodeStore, Store) groups
    by_name = {s.legacy_name: s for s in suggestions}
    assert len(by_name["PHARMACY MAINSTORE DRUGS"].raw_rows) == 2
    assert len(by_name["EMERGENCY"].raw_rows) == 2
    # No Groq key -- fallback path, no clustering and no AI suggestion,
    # admin must supply everything manually.
    assert by_name["EMERGENCY"].consolidated_legacy_names == []
    assert by_name["EMERGENCY"].suggested_warehouse_type_code is None
    assert "AI unavailable" in by_name["EMERGENCY"].reasoning


def test_build_clustered_candidates_merges_billing_variants():
    """Direct test of the pure merge step (no Groq call needed) -- mirrors
    the real RSUS Mapping.xlsx consolidation pattern: several billing/
    status-variant legacy names fold into one candidate for the same
    physical warehouse."""
    candidates = [
        {"legacy_code": "RSUS-1", "legacy_name": "PHARMACY MAINSTORE DRUGS", "raw_rows": [{"code_rack": "P1", "description": "DRUGS - A", "is_active": True}]},
        {"legacy_code": "RSUS-3", "legacy_name": "PHARMACY MAINSTORE DRUGS BPJS", "raw_rows": [{"code_rack": "P2", "description": "DRUGS - B", "is_active": True}]},
        {"legacy_code": "RSUS-16", "legacy_name": "OPD 2ND FLOOR", "raw_rows": [{"code_rack": "O1", "description": "MISC", "is_active": True}]},
    ]
    # Group 1: indices 0 and 1 (the two Pharmacy variants) merge; group 2:
    # index 2 (OPD) stays on its own, matching the real "don't merge floor
    # variants" behavior.
    groups = [[0, 1], [2]]

    merged = _build_clustered_candidates(candidates, groups)

    assert len(merged) == 2
    pharmacy = merged[0]
    assert pharmacy["legacy_code"] == "RSUS-1"
    assert pharmacy["legacy_name"] == "PHARMACY MAINSTORE DRUGS"
    assert pharmacy["consolidated_legacy_names"] == ["PHARMACY MAINSTORE DRUGS BPJS"]
    assert [r["description"] for r in pharmacy["raw_rows"]] == ["DRUGS - A", "DRUGS - B"]

    opd = merged[1]
    assert opd["legacy_name"] == "OPD 2ND FLOOR"
    assert opd["consolidated_legacy_names"] == []
    assert len(opd["raw_rows"]) == 1


def test_upload_without_ai_never_consolidates(db, seeded):
    """Without a Groq key, clustering falls back to every candidate as its
    own group -- i.e. today's pre-clustering behavior, never a surprise
    merge."""
    rows = RAW_ROWS + [
        ["RUMAH SAKIT UMUM SILOAM", "RSUS-3", "PHARMACY MAINSTORE DRUGS BPJS", "P99", "DRUGS - MISC", 1],
    ]
    content = _raw_xlsx_bytes(rows)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    names = {s.legacy_name for s in suggestions}
    assert "PHARMACY MAINSTORE DRUGS" in names
    assert "PHARMACY MAINSTORE DRUGS BPJS" in names
    assert len(suggestions) == 3  # stayed separate, not folded into 2


def test_upload_skips_incomplete_rows(db, seeded):
    rows = RAW_ROWS + [["ORG", "RSUS-99", "", "X", "some rack", 1]]  # missing Store
    content = _raw_xlsx_bytes(rows)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    assert len(suggestions) == 2  # the incomplete row didn't create a 3rd group


def test_upload_rejects_missing_columns(db, seeded):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Organization", "CodeStore", "Store"])  # missing CodeStoreRack/StoreRack
    ws.append(["ORG", "RSUS-1", "PHARMACY"])
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(HTTPException) as exc_info:
        upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "bad.xlsx", buf.getvalue())
    assert exc_info.value.status_code == 400


def test_upload_rejects_unknown_site(db, seeded):
    import uuid

    content = _raw_xlsx_bytes(RAW_ROWS)
    with pytest.raises(HTTPException) as exc_info:
        upload_raw_import(db, seeded["admin"].id, uuid.uuid4(), "raw.xlsx", content)
    assert exc_info.value.status_code == 400


def test_approve_warehouse_suggestion_with_override_creates_warehouse(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    emergency = next(s for s in suggestions if s.legacy_name == "EMERGENCY")

    resolved = approve_warehouse_suggestion(
        db, emergency.id, warehouse_type_code="A", warehouse_code="08", name=None, description=None, capacity=None
    )
    assert resolved.status == "approved"
    assert resolved.created_warehouse_id is not None
    warehouse = db.get(Warehouse, resolved.created_warehouse_id)
    assert warehouse.generated_code == "RSUS-A08"
    assert warehouse.name == "EMERGENCY"


def test_approve_warehouse_suggestion_without_override_and_no_ai_suggestion_fails(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    emergency = suggestions[0]

    with pytest.raises(HTTPException) as exc_info:
        approve_warehouse_suggestion(
            db, emergency.id, warehouse_type_code=None, warehouse_code=None, name=None, description=None, capacity=None
        )
    assert exc_info.value.status_code == 400


def test_reject_warehouse_suggestion_creates_nothing(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)

    resolved = reject_warehouse_suggestion(db, suggestions[0].id)
    assert resolved.status == "rejected"
    assert db.scalar(select(Warehouse)) is None


def test_approve_already_resolved_warehouse_suggestion_conflicts(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    reject_warehouse_suggestion(db, suggestions[0].id)

    with pytest.raises(HTTPException) as exc_info:
        approve_warehouse_suggestion(
            db, suggestions[0].id, warehouse_type_code="A", warehouse_code="08", name=None, description=None, capacity=None
        )
    assert exc_info.value.status_code == 409


def test_generate_location_suggestions_only_covers_approved_warehouses(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    emergency = next(s for s in suggestions if s.legacy_name == "EMERGENCY")

    approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )
    # emergency stays pending, unapproved

    created = generate_location_suggestions(db, batch.id)
    assert len(created) == 2  # only pharmacy's 2 racks -- emergency's are excluded
    assert all(c.warehouse_suggestion_id == pharmacy.id for c in created)
    assert all(c.suggested_category_rack is None for c in created)  # fallback path


def test_generate_location_suggestions_is_idempotent(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )

    first = generate_location_suggestions(db, batch.id)
    second = generate_location_suggestions(db, batch.id)
    assert len(first) == 2
    assert len(second) == 0  # already covered, no duplicates
    assert len(list(db.scalars(select(RawLocationSuggestion)).all())) == 2


def test_approve_location_suggestion_with_override_creates_location(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )
    generate_location_suggestions(db, batch.id)

    loc_suggestion = db.scalar(
        select(RawLocationSuggestion).where(RawLocationSuggestion.legacy_description == "DRUGS - RAK 1")
    )
    resolved = approve_location_suggestion(db, loc_suggestion.id, category_rack="DRUGS", description=None)
    assert resolved.status == "approved"
    assert resolved.created_location_id is not None
    location = db.get(Location, resolved.created_location_id)
    assert location.description == "DRUGS - RAK 1"


def test_approve_location_suggestion_triggers_merge_suggestion_when_similar(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    resolved_wh = approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )
    # Pre-create a location with a near-identical description to the raw
    # "DRUGS - RAK 1" row -- differently worded but almost certainly the
    # same real place.
    create_location(db, resolved_wh.created_warehouse_id, "A", "DRUGS", "DRUGS - RAK 1 ")

    generate_location_suggestions(db, batch.id)
    loc_suggestion = db.scalar(
        select(RawLocationSuggestion).where(RawLocationSuggestion.legacy_description == "DRUGS - RAK 1")
    )
    resolved = approve_location_suggestion(db, loc_suggestion.id, category_rack="DRUGS", description=None)

    assert resolved.status == "approved"
    assert resolved.created_location_id is None
    assert resolved.created_merge_suggestion_id is not None
    assert db.get(MergeSuggestion, resolved.created_merge_suggestion_id) is not None
    # Still only the one pre-created location -- no duplicate was made.
    assert len(list(db.scalars(select(Location)).all())) == 1


def test_reject_location_suggestion(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )
    generate_location_suggestions(db, batch.id)

    loc_suggestion = db.scalar(select(RawLocationSuggestion))
    resolved = reject_location_suggestion(db, loc_suggestion.id)
    assert resolved.status == "rejected"
    assert db.scalar(select(Location)) is None


def test_confirmed_warehouse_examples_reflects_final_applied_value(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    _batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    emergency = next(s for s in suggestions if s.legacy_name == "EMERGENCY")
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")

    # Approved as the AI's own suggestion would have been (here: an explicit
    # override, since fallback path has no AI suggestion) -- either way the
    # final applied value is what should show up as a confirmed example.
    approve_warehouse_suggestion(
        db, emergency.id, warehouse_type_code="A", warehouse_code="08", name=None, description=None, capacity=None
    )
    # Left pending -- must NOT appear as a confirmed example yet.
    assert pharmacy.status == "pending"

    examples = confirmed_warehouse_examples(db)
    assert ("EMERGENCY", "A", "08") in examples
    assert not any(name == "PHARMACY MAINSTORE DRUGS" for name, _t, _c in examples)


def test_confirmed_location_examples_reflects_final_applied_value(db, seeded):
    content = _raw_xlsx_bytes(RAW_ROWS)
    batch, suggestions = upload_raw_import(db, seeded["admin"].id, seeded["site"].id, "raw.xlsx", content)
    pharmacy = next(s for s in suggestions if s.legacy_name == "PHARMACY MAINSTORE DRUGS")
    approve_warehouse_suggestion(
        db, pharmacy.id, warehouse_type_code="A", warehouse_code="01", name=None, description=None, capacity=None
    )
    generate_location_suggestions(db, batch.id)

    loc_suggestion = db.scalar(
        select(RawLocationSuggestion).where(RawLocationSuggestion.legacy_description == "DRUGS - RAK 1")
    )
    approve_location_suggestion(db, loc_suggestion.id, category_rack="DRUGS", description=None)

    examples = confirmed_location_examples(db)
    assert ("A", "DRUGS - RAK 1", "DRUGS") in examples
    # The still-pending "DRUGS - RAK 2" row must not appear yet.
    assert not any(desc == "DRUGS - RAK 2" for _t, desc, _c in examples)
