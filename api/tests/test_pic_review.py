"""HTTP-level tests for the PIC acknowledgment workflow: the reverse
direction of the existing Revision workflow -- an admin creates/edits a
Warehouse or Location, and the PIC for that Hospital Unit explicitly
confirms they've reviewed and agree with the current coding. Any
subsequent edit (admin PATCH, or an applied Revision) clears that
acknowledgment back to "needs review"."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.location_service import create_location
from app.services.warehouse_service import create_warehouse
import app.models as _models  # noqa: F401  -- registers every model on Base.metadata


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    from app.core.security import hash_password
    from app.models.user import User

    site_a = Site(code="RSUS", name="Rumah Sakit Umum Siloam", short_code="US")
    site_b = Site(code="SHMD", name="Siloam Hospitals Medan", short_code="MD")
    db.add(site_a)
    db.add(site_b)
    db.add(WarehouseTypeConfig(code="A", description="Non-General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="01", description="Pharmacy Mainstore"))
    drugs = LocationTypeConfig(warehouse_type_code="A", code="A", description="Drugs/Consumables")
    db.add(drugs)
    db.add(User(full_name="Admin", email="admin@test.com", password_hash=hash_password("adminpass"), role="admin"))
    db.flush()
    db.add(CategoryRackMapping(warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs.id))
    db.add(
        User(
            full_name="PIC RSUS", email="pic@test.com", password_hash=hash_password("picpass"),
            role="pic", site_id=site_a.id,
        )
    )
    db.add(
        User(
            full_name="PIC SHMD", email="pic-shmd@test.com", password_hash=hash_password("picpass2"),
            role="pic", site_id=site_b.id,
        )
    )
    db.commit()

    warehouse_a = create_warehouse(db, site_a.id, "A", "01", "RSUS Pharmacy", None, None)
    location_a = create_location(db, warehouse_a.id, "A", "DRUGS", "Loc A1")
    db.commit()

    test_client = TestClient(app)
    yield test_client, db, site_a, site_b, warehouse_a, location_a

    app.dependency_overrides.clear()
    db.close()


def _login(client: TestClient, email: str, password: str) -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_new_warehouse_needs_pic_review(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.get(f"/warehouses/{warehouse_a.id}", headers={"Authorization": f"Bearer {admin_token}"})
    body = res.json()
    assert body["needs_pic_review"] is True
    assert body["pic_acknowledged_at"] is None
    assert body["pic_acknowledged_by"] is None


def test_pic_acknowledges_warehouse(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["needs_pic_review"] is False
    assert body["pic_acknowledged_at"] is not None


def test_admin_cannot_acknowledge_warehouse(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.post(
        f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 403


def test_pic_cannot_acknowledge_another_sites_warehouse(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    other_pic_token = _login(test_client, "pic-shmd@test.com", "picpass2")

    res = test_client.post(
        f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {other_pic_token}"}
    )
    assert res.status_code == 403


def test_admin_direct_edit_resets_pic_acknowledgment(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    test_client.post(f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"})

    res = test_client.patch(
        f"/warehouses/{warehouse_a.id}", json={"capacity": 50}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["needs_pic_review"] is True
    assert res.json()["pic_acknowledged_at"] is None


def test_approved_revision_resets_pic_acknowledgment(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    test_client.post(f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"})
    confirm = test_client.get(f"/warehouses/{warehouse_a.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert confirm.json()["needs_pic_review"] is False

    submit = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse", "entity_id": str(warehouse_a.id),
            "proposed_value": {"name": "Renamed"}, "comment": "test",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    revision_id = submit.json()["id"]
    test_client.post(f"/revisions/{revision_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})

    res = test_client.get(f"/warehouses/{warehouse_a.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.json()["needs_pic_review"] is True
    assert res.json()["pic_acknowledged_at"] is None


def test_has_pending_pic_review_filter(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    second = create_warehouse(db, site_a.id, "A", "01", "RSUS Pharmacy Two", None, None)
    db.commit()
    test_client.post(f"/warehouses/{warehouse_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"})

    res = test_client.get(
        "/warehouses", params={"has_pending_pic_review": True}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    codes = [w["generated_code"] for w in res.json()]
    assert codes == [second.generated_code]

    res2 = test_client.get(
        "/warehouses", params={"has_pending_pic_review": False}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    codes2 = [w["generated_code"] for w in res2.json()]
    assert codes2 == [warehouse_a.generated_code]


def test_pic_acknowledges_location(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        f"/locations/{location_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["needs_pic_review"] is False


def test_pic_cannot_acknowledge_location_in_another_site(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    other_pic_token = _login(test_client, "pic-shmd@test.com", "picpass2")

    res = test_client.post(
        f"/locations/{location_a.id}/acknowledge", headers={"Authorization": f"Bearer {other_pic_token}"}
    )
    assert res.status_code == 403


def test_admin_direct_edit_resets_location_pic_acknowledgment(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    test_client.post(f"/locations/{location_a.id}/acknowledge", headers={"Authorization": f"Bearer {pic_token}"})

    res = test_client.patch(
        f"/locations/{location_a.id}", json={"description": "Loc A1 v2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["needs_pic_review"] is True


def test_pic_dashboard_summary_scoped_to_own_site(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    create_warehouse(db, site_b.id, "A", "01", "SHMD Pharmacy", None, None)
    db.commit()

    res = test_client.get("/dashboard/pic-summary", headers={"Authorization": f"Bearer {pic_token}"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["warehouses"]["total_warehouses"] == 1  # only site_a's warehouse, not site_b's
    assert body["locations"]["total_locations"] == 1


def test_admin_cannot_access_pic_dashboard_summary(client):
    test_client, db, site_a, site_b, warehouse_a, location_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.get("/dashboard/pic-summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 403
