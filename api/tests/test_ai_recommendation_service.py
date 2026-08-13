"""Tests the no-key fallback path -- deliberately forces
`settings.groq_api_key` to None for every test here (via monkeypatch),
regardless of whatever real key a developer's local .env happens to have
(e.g. after the live-verification step in the README). Without that, these
tests would silently make real Groq calls -- flaky, slow, and the model's
exact wording isn't something a test should assert on. Confirms the
feature produces correct, real recommendations even without any AI call,
and that generation is idempotent (re-running replaces, doesn't
duplicate)."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.recommendation import Recommendation
from app.models.site import Site
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.ai_recommendation_service import generate_recommendations
from app.services.location_service import create_location
from app.services.warehouse_service import create_warehouse

import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def _no_groq_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)


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
    for code in ("01", "02", "03"):
        db.add(WarehouseCodeConfig(warehouse_type_code="A", code=code, description=f"WH {code}"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.commit()
    return site


def test_no_candidates_produces_no_recommendations(db, seeded):
    assert generate_recommendations(db) == []


def test_redundant_warehouse_produces_a_recommendation(db, seeded):
    create_warehouse(db, seeded.id, "A", "01", "Empty WH", None, capacity=10)
    recs = generate_recommendations(db)
    assert len(recs) == 1
    assert recs[0].category == "redundant_warehouse"
    assert "Empty WH" in recs[0].explanation


def test_merge_candidate_produces_a_recommendation_referencing_both_warehouses(db, seeded):
    a = create_warehouse(db, seeded.id, "A", "01", "Warehouse A", None, capacity=10)
    b = create_warehouse(db, seeded.id, "A", "02", "Warehouse B", None, capacity=10)
    create_location(db, a.id, "A", "DRUGS", "Loc A1")
    create_location(db, b.id, "A", "DRUGS", "Loc B1")

    recs = generate_recommendations(db)
    assert len(recs) == 1
    assert recs[0].category == "merge_opportunity"
    assert set(recs[0].warehouse_ids) == {str(a.id), str(b.id)}
    assert "Warehouse A" in recs[0].explanation and "Warehouse B" in recs[0].explanation


def test_generate_replaces_previous_recommendations_not_duplicates(db, seeded):
    create_warehouse(db, seeded.id, "A", "01", "Empty WH", None, capacity=10)
    generate_recommendations(db)
    generate_recommendations(db)  # run again, nothing changed
    assert len(list(db.scalars(select(Recommendation)).all())) == 1


def test_generate_clears_stale_recommendations_when_situation_resolves(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Empty WH", None, capacity=10)
    generate_recommendations(db)
    assert len(list(db.scalars(select(Recommendation)).all())) == 1

    # Push occupancy to 50% (5/10) -- past the empty AND underutilized
    # thresholds into "normal," not just past "empty."
    for i in range(5):
        create_location(db, wh.id, "A", "DRUGS", f"Loc {i}")
    generate_recommendations(db)
    assert list(db.scalars(select(Recommendation)).all()) == []
