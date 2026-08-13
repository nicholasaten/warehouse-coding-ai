"""HTTP-level tests for the Warehouse & Location Review Workflow: a PIC
submits a revision proposing new values for a record in their own Hospital
Unit; the record is never changed until an Admin approves, rejects, or
edits-and-approves it."""

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
            full_name="PIC RSUS",
            email="pic@test.com",
            password_hash=hash_password("picpass"),
            role="pic",
            site_id=site_a.id,
        )
    )
    db.commit()

    warehouse_a = create_warehouse(db, site_a.id, "A", "01", "RSUS Pharmacy", None, None)
    warehouse_b = create_warehouse(db, site_b.id, "A", "01", "SHMD Pharmacy", None, None)
    location_a = create_location(db, warehouse_a.id, "A", "DRUGS", "Loc A1")
    db.commit()

    test_client = TestClient(app)
    yield test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a

    app.dependency_overrides.clear()
    db.close()


def _login(client: TestClient, email: str, password: str) -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_pic_submits_revision_for_own_site_warehouse(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"name": "RSUS Pharmacy Mainstore"},
            "comment": "Name was abbreviated, should be the full name",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending"
    assert body["original_value"] == {"name": "RSUS Pharmacy"}
    assert body["proposed_value"] == {"name": "RSUS Pharmacy Mainstore"}

    # The warehouse itself must be untouched until an admin reviews it.
    db.expire_all()
    assert warehouse_a.name == "RSUS Pharmacy"


def test_pic_cannot_submit_revision_for_another_sites_warehouse(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_b.id),
            "proposed_value": {"name": "Sneaky rename"},
            "comment": "not mine",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    assert res.status_code == 403


def test_pic_cannot_propose_a_formula_driving_field(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"warehouse_code": "02"},
            "comment": "trying to sneak a formula field through",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    assert res.status_code == 400


def test_admin_approve_applies_the_proposed_value(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    submit = test_client.post(
        "/revisions",
        json={
            "entity_type": "location",
            "entity_id": str(location_a.id),
            "proposed_value": {"description": "Loc A1 - Corrected"},
            "comment": "Typo in original description",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    revision_id = submit.json()["id"]

    queue = test_client.get("/revisions", headers={"Authorization": f"Bearer {admin_token}"})
    assert queue.status_code == 200
    assert len(queue.json()) == 1

    approve = test_client.post(
        f"/revisions/{revision_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve.status_code == 200
    body = approve.json()
    assert body["status"] == "approved"
    assert body["final_value"] == {"description": "Loc A1 - Corrected"}

    db.expire_all()
    db.refresh(location_a)
    assert location_a.description == "Loc A1 - Corrected"


def test_admin_reject_leaves_entity_unchanged(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    submit = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"capacity": 500},
            "comment": "Think capacity is wrong",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    revision_id = submit.json()["id"]

    reject = test_client.post(
        f"/revisions/{revision_id}/reject",
        json={"reason": "Capacity was verified correct on-site last month"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject.status_code == 200
    body = reject.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Capacity was verified correct on-site last month"
    assert body["final_value"] is None

    db.expire_all()
    db.refresh(warehouse_a)
    assert warehouse_a.capacity is None


def test_admin_edit_and_approve_applies_admins_value_not_pics(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    submit = test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"name": "RSUS Pharmacyy"},
            "comment": "Fixing the name",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    revision_id = submit.json()["id"]

    edit_approve = test_client.post(
        f"/revisions/{revision_id}/edit-approve",
        json={"final_value": {"name": "RSUS Pharmacy Mainstore"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert edit_approve.status_code == 200
    body = edit_approve.json()
    assert body["status"] == "approved"
    assert body["proposed_value"] == {"name": "RSUS Pharmacyy"}
    assert body["final_value"] == {"name": "RSUS Pharmacy Mainstore"}

    db.expire_all()
    db.refresh(warehouse_a)
    assert warehouse_a.name == "RSUS Pharmacy Mainstore"


def test_pic_only_sees_their_own_submitted_revisions(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    from app.core.security import hash_password
    from app.models.user import User

    other_pic = User(
        full_name="PIC SHMD",
        email="pic-shmd@test.com",
        password_hash=hash_password("picpass2"),
        role="pic",
        site_id=site_b.id,
    )
    db.add(other_pic)
    db.commit()

    pic_token = _login(test_client, "pic@test.com", "picpass")
    other_pic_token = _login(test_client, "pic-shmd@test.com", "picpass2")

    test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"name": "RSUS renamed"},
            "comment": "test",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_b.id),
            "proposed_value": {"name": "SHMD renamed"},
            "comment": "test",
        },
        headers={"Authorization": f"Bearer {other_pic_token}"},
    )

    res = test_client.get("/revisions", headers={"Authorization": f"Bearer {pic_token}"})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["proposed_value"] == {"name": "RSUS renamed"}


def test_admin_can_edit_warehouse_directly_via_patch(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.patch(
        f"/warehouses/{warehouse_a.id}",
        json={"capacity": 999},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["capacity"] == 999


def test_pic_cannot_edit_warehouse_directly_via_patch(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.patch(
        f"/warehouses/{warehouse_a.id}",
        json={"capacity": 999},
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    assert res.status_code == 403


def test_warehouse_list_reports_has_pending_revision(client):
    test_client, db, site_a, site_b, warehouse_a, warehouse_b, location_a = client
    pic_token = _login(test_client, "pic@test.com", "picpass")
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    test_client.post(
        "/revisions",
        json={
            "entity_type": "warehouse",
            "entity_id": str(warehouse_a.id),
            "proposed_value": {"name": "Renamed"},
            "comment": "test",
        },
        headers={"Authorization": f"Bearer {pic_token}"},
    )

    res = test_client.get(
        "/warehouses", params={"has_pending_revision": True}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    codes = [w["generated_code"] for w in res.json()]
    assert codes == [warehouse_a.generated_code]
