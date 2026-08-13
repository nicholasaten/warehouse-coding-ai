"""Full HTTP-level tests for the admin/pic role system: a PIC can only see
their own site's warehouses/locations, can never create/edit directly, and
an admin can create PIC accounts scoped to a site."""

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

    # Seed two sites + minimal config, and one admin, directly via a real
    # session (bypassing the API, same convention as every other test file).
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
    db.commit()

    warehouse_a = create_warehouse(db, site_a.id, "A", "01", "RSUS Pharmacy", None, None)
    db.commit()

    test_client = TestClient(app)
    yield test_client, db, site_a, site_b, warehouse_a

    app.dependency_overrides.clear()
    db.close()


def _login(client: TestClient, email: str, password: str) -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_admin_can_create_pic_scoped_to_a_site(client):
    test_client, db, site_a, site_b, _wh = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.post(
        "/users",
        json={"full_name": "PIC RSUS", "email": "pic@test.com", "password": "picpass", "role": "pic", "site_id": str(site_a.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "pic"
    assert body["site_id"] == str(site_a.id)


def test_pic_without_site_id_is_rejected(client):
    test_client, db, site_a, site_b, _wh = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    res = test_client.post(
        "/users",
        json={"full_name": "Bad PIC", "email": "bad@test.com", "password": "x", "role": "pic"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422


def test_pic_only_sees_their_own_site_warehouses(client):
    test_client, db, site_a, site_b, warehouse_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")

    # Create a second warehouse under site_b, and a PIC scoped to site_a.
    create_warehouse(db, site_b.id, "A", "01", "SHMD Pharmacy", None, None)
    db.commit()

    test_client.post(
        "/users",
        json={"full_name": "PIC RSUS", "email": "pic@test.com", "password": "picpass", "role": "pic", "site_id": str(site_a.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    pic_token = _login(test_client, "pic@test.com", "picpass")
    res = test_client.get("/warehouses", headers={"Authorization": f"Bearer {pic_token}"})
    assert res.status_code == 200
    codes = [w["generated_code"] for w in res.json()]
    assert codes == [warehouse_a.generated_code]  # only their own site, not SHMD's


def test_pic_cannot_create_a_warehouse_directly(client):
    test_client, db, site_a, site_b, _wh = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")
    test_client.post(
        "/users",
        json={"full_name": "PIC RSUS", "email": "pic@test.com", "password": "picpass", "role": "pic", "site_id": str(site_a.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res = test_client.post(
        "/warehouses",
        json={"site_id": str(site_a.id), "warehouse_type_code": "A", "warehouse_code": "01", "name": "Sneaky WH"},
        headers={"Authorization": f"Bearer {pic_token}"},
    )
    assert res.status_code == 403


def test_pic_cannot_view_another_sites_warehouse_by_id(client):
    test_client, db, site_a, site_b, warehouse_a = client
    admin_token = _login(test_client, "admin@test.com", "adminpass")
    warehouse_b = create_warehouse(db, site_b.id, "A", "01", "SHMD Pharmacy", None, None)
    db.commit()

    test_client.post(
        "/users",
        json={"full_name": "PIC RSUS", "email": "pic@test.com", "password": "picpass", "role": "pic", "site_id": str(site_a.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    pic_token = _login(test_client, "pic@test.com", "picpass")

    res_own = test_client.get(f"/warehouses/{warehouse_a.id}", headers={"Authorization": f"Bearer {pic_token}"})
    assert res_own.status_code == 200

    res_other = test_client.get(f"/warehouses/{warehouse_b.id}", headers={"Authorization": f"Bearer {pic_token}"})
    assert res_other.status_code == 403
