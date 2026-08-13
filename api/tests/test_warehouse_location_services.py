"""Exercises the stateful parts of warehouse_service/location_service that
the pure id_generator_service tests can't cover -- the duplicate-letter
renumbering side effect, the staging-receive reserved bucket, and the
whole-warehouse dedup guard. Runs against an isolated in-memory SQLite DB,
not the real Postgres/Neon database."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.revision import Revision
from app.models.site import Site
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig
from app.services.location_service import create_location, delete_location, reassign_location_warehouse
from app.services.warehouse_service import create_warehouse, delete_warehouse, merge_warehouse

import app.models  # noqa: F401  -- registers every model on Base.metadata


@pytest.fixture()
def db():
    # FK enforcement is off by default on SQLite -- turn it on so the
    # delete-cascade tests below actually exercise the same ON DELETE
    # CASCADE/SET NULL behavior the real Postgres schema enforces (see
    # migration 0009), not just an unenforced FK column.
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def seeded(db):
    site = Site(code="RSUS", name="Rumah Sakit Umum Siloam", short_code="US")
    db.add(site)
    db.add(WarehouseTypeConfig(code="A", description="Non-General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="01", description="Pharmacy Mainstore"))
    drugs_loc_type = LocationTypeConfig(
        warehouse_type_code="A", code="A", description="Drugs/Consumables", is_whole_warehouse=False
    )
    all_loc_type = LocationTypeConfig(warehouse_type_code="A", code="H", description="All", is_whole_warehouse=True)
    db.add(drugs_loc_type)
    db.add(all_loc_type)
    db.flush()
    db.add(
        CategoryRackMapping(
            warehouse_type_code="A", raw_category_text="DRUGS", location_type_config_id=drugs_loc_type.id
        )
    )
    db.commit()
    return site


def test_lone_warehouse_has_no_duplicate_suffix(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    assert wh.generated_code == "RSUS-A01"
    assert wh.duplicate_letter is None


def test_second_warehouse_in_group_relabels_the_first(db, seeded):
    first = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    assert first.generated_code == "RSUS-A01"

    second = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Consumables", None, None)

    db.refresh(first)
    assert first.generated_code == "RSUS-A01A"
    assert first.duplicate_letter == "A"
    assert second.generated_code == "RSUS-A01B"
    assert second.duplicate_letter == "B"


def test_location_sequence_increments_within_warehouse(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc1 = create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    loc2 = create_location(db, wh.id, "A", "DRUGS", "DRUGS - OBAT-OBAT TERTENTU")
    assert loc1.generated_code == "USA01-A01"
    assert loc2.generated_code == "USA01-A02"


def test_staging_receive_always_gets_seq_99(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")  # seq 01
    staging = create_location(db, wh.id, "A", "MISC", "STAGING RECEIVE")
    normal_again = create_location(db, wh.id, "A", "DRUGS", "DRUGS - TABLET")
    assert staging.generated_code == "USA01-A99"
    assert normal_again.generated_code == "USA01-A02"  # staging's 99 didn't push the normal counter


def test_whole_warehouse_location_omits_seq_and_is_unique(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh.id, "H", "ALL", "ANCILLARY SERVICES - ALL")
    assert loc.generated_code == "USA01-H"

    with pytest.raises(Exception):
        create_location(db, wh.id, "H", "ALL", "A SECOND ALL LOCATION")


def test_delete_warehouse_cascades_its_locations(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    loc_id = loc.id

    delete_warehouse(db, wh.id)

    # The Location row was removed by the DB-level ON DELETE CASCADE, not
    # by the ORM directly -- expire the session's stale identity-map copy
    # first, otherwise db.get() raises ObjectDeletedError instead of
    # returning None for an object it still thinks is loaded.
    db.expire_all()
    assert db.get(Warehouse, wh.id) is None
    assert db.get(Location, loc_id) is None


def test_delete_warehouse_blocked_by_pending_revision(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    from app.models.user import User

    pic = User(full_name="PIC", email="pic@test.com", password_hash="x", role="pic", site_id=seeded.id)
    db.add(pic)
    db.flush()
    db.add(
        Revision(
            entity_type="warehouse", entity_id=wh.id, submitted_by=pic.id,
            original_value={"name": "Pharmacy Mainstore Drugs"}, proposed_value={"name": "Renamed"}, comment="test",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_warehouse(db, wh.id)
    assert exc_info.value.status_code == 409
    assert db.get(Warehouse, wh.id) is not None  # untouched


def test_delete_warehouse_not_found(db, seeded):
    with pytest.raises(HTTPException) as exc_info:
        delete_warehouse(db, uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_delete_warehouse_does_not_reletter_surviving_sibling(db, seeded):
    first = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    second = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Consumables", None, None)
    assert second.generated_code == "RSUS-A01B"

    delete_warehouse(db, first.id)

    db.refresh(second)
    # Still labeled "B" even though it's now the only one left in the
    # group -- deliberately not re-lettered, see delete_warehouse's
    # docstring for why.
    assert second.generated_code == "RSUS-A01B"
    assert second.duplicate_letter == "B"


def test_delete_location_success(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")

    delete_location(db, loc.id)

    assert db.get(Location, loc.id) is None
    assert db.get(Warehouse, wh.id) is not None  # warehouse itself untouched


def test_delete_location_blocked_by_pending_revision(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    from app.models.user import User

    pic = User(full_name="PIC", email="pic2@test.com", password_hash="x", role="pic", site_id=seeded.id)
    db.add(pic)
    db.flush()
    db.add(
        Revision(
            entity_type="location", entity_id=loc.id, submitted_by=pic.id,
            original_value={"description": "DRUGS - PSIKOTROPIKA"}, proposed_value={"description": "Renamed"},
            comment="test",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_location(db, loc.id)
    assert exc_info.value.status_code == 409
    assert db.get(Location, loc.id) is not None  # untouched


def test_delete_location_not_found(db, seeded):
    with pytest.raises(HTTPException) as exc_info:
        delete_location(db, uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_reassign_location_warehouse_success(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    wh2 = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc = create_location(db, wh1.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    assert loc.generated_code == "USA01-A01"

    moved = reassign_location_warehouse(db, loc.id, wh2.id)

    assert moved.warehouse_id == wh2.id
    assert moved.generated_code == "USA02-A01"
    assert moved.seq == 1


def test_reassign_location_warehouse_assigns_next_free_seq_in_target(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    wh2 = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    create_location(db, wh2.id, "A", "DRUGS", "DRUGS - EXISTING")  # takes seq 1 in wh2
    loc = create_location(db, wh1.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")

    moved = reassign_location_warehouse(db, loc.id, wh2.id)

    assert moved.generated_code == "USA02-A02"  # next free seq in wh2, not wh1's own seq


def test_reassign_location_warehouse_same_warehouse_blocked(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")

    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, loc.id, wh.id)
    assert exc_info.value.status_code == 400


def test_reassign_location_warehouse_blocked_by_pending_revision(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    wh2 = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc = create_location(db, wh1.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    from app.models.user import User

    pic = User(full_name="PIC", email="pic3@test.com", password_hash="x", role="pic", site_id=seeded.id)
    db.add(pic)
    db.flush()
    db.add(
        Revision(
            entity_type="location", entity_id=loc.id, submitted_by=pic.id,
            original_value={"description": "DRUGS - PSIKOTROPIKA"}, proposed_value={"description": "Renamed"},
            comment="test",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, loc.id, wh2.id)
    assert exc_info.value.status_code == 409


def test_reassign_location_warehouse_invalid_location_type_under_target(db, seeded):
    db.add(WarehouseTypeConfig(code="B", description="General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="B", code="01", description="Logistics"))
    db.commit()
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    wh2 = create_warehouse(db, seeded.id, "B", "01", "Logistics", None, None)
    loc = create_location(db, wh1.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")

    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, loc.id, wh2.id)
    assert exc_info.value.status_code == 400


def test_reassign_location_warehouse_whole_warehouse_conflict(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    wh2 = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc = create_location(db, wh1.id, "H", "ALL", "ANCILLARY SERVICES - ALL")
    create_location(db, wh2.id, "H", "ALL", "ANCILLARY SERVICES - ALL 2")  # wh2 already has its own whole-wh loc

    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, loc.id, wh2.id)
    assert exc_info.value.status_code == 409


def test_reassign_location_warehouse_not_found(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, uuid.uuid4(), wh.id)
    assert exc_info.value.status_code == 404


def test_reassign_location_warehouse_target_not_found(db, seeded):
    wh1 = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    loc = create_location(db, wh1.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    with pytest.raises(HTTPException) as exc_info:
        reassign_location_warehouse(db, loc.id, uuid.uuid4())
    assert exc_info.value.status_code == 400


def test_merge_warehouse_moves_locations_and_deletes_source(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc1 = create_location(db, source.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    loc2 = create_location(db, source.id, "A", "DRUGS", "DRUGS - TABLET")
    loc1_id, loc2_id, source_id = loc1.id, loc2.id, source.id

    merged_target = merge_warehouse(db, source.id, target.id)

    assert merged_target.id == target.id
    db.expire_all()
    assert db.get(Warehouse, source_id) is None
    moved1 = db.get(Location, loc1_id)
    moved2 = db.get(Location, loc2_id)
    assert {moved1.warehouse_id, moved2.warehouse_id} == {target.id}
    assert {moved1.generated_code, moved2.generated_code} == {"USA02-A01", "USA02-A02"}


def test_merge_warehouse_self_merge_blocked(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, wh.id, wh.id)
    assert exc_info.value.status_code == 400


def test_merge_warehouse_cross_site_blocked(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    other_site = Site(code="SHMD", name="Siloam Hospitals Medan", short_code="MD")
    db.add(other_site)
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, other_site.id, "A", "02", "Pharmacy Outpatient", None, None)

    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, source.id, target.id)
    assert exc_info.value.status_code == 400


def test_merge_warehouse_blocked_by_pending_revision_on_source(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    from app.models.user import User

    pic = User(full_name="PIC", email="pic4@test.com", password_hash="x", role="pic", site_id=seeded.id)
    db.add(pic)
    db.flush()
    db.add(
        Revision(
            entity_type="warehouse", entity_id=source.id, submitted_by=pic.id,
            original_value={"name": "Pharmacy Mainstore Drugs"}, proposed_value={"name": "Renamed"}, comment="test",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, source.id, target.id)
    assert exc_info.value.status_code == 409


def test_merge_warehouse_blocked_by_pending_revision_on_a_location(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc = create_location(db, source.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")
    from app.models.user import User

    pic = User(full_name="PIC", email="pic5@test.com", password_hash="x", role="pic", site_id=seeded.id)
    db.add(pic)
    db.flush()
    db.add(
        Revision(
            entity_type="location", entity_id=loc.id, submitted_by=pic.id,
            original_value={"description": "DRUGS - PSIKOTROPIKA"}, proposed_value={"description": "Renamed"},
            comment="test",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, source.id, target.id)
    assert exc_info.value.status_code == 409
    # atomic -- source and its location must be untouched, not half-merged
    db.expire_all()
    assert db.get(Warehouse, source.id) is not None
    assert db.get(Location, loc.id).warehouse_id == source.id


def test_merge_warehouse_invalid_location_type_under_target_blocked(db, seeded):
    db.add(WarehouseTypeConfig(code="B", description="General Items"))
    db.add(WarehouseCodeConfig(warehouse_type_code="B", code="01", description="Logistics"))
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, seeded.id, "B", "01", "Logistics", None, None)
    loc = create_location(db, source.id, "A", "DRUGS", "DRUGS - PSIKOTROPIKA")

    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, source.id, target.id)
    assert exc_info.value.status_code == 400
    db.expire_all()
    assert db.get(Warehouse, source.id) is not None
    assert db.get(Location, loc.id).warehouse_id == source.id


def test_merge_warehouse_whole_warehouse_conflict_blocked(db, seeded):
    db.add(WarehouseCodeConfig(warehouse_type_code="A", code="02", description="Pharmacy Outpatient"))
    db.commit()
    source = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    target = create_warehouse(db, seeded.id, "A", "02", "Pharmacy Outpatient", None, None)
    loc = create_location(db, source.id, "H", "ALL", "ANCILLARY SERVICES - ALL")
    create_location(db, target.id, "H", "ALL", "ANCILLARY SERVICES - ALL 2")

    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, source.id, target.id)
    assert exc_info.value.status_code == 409
    db.expire_all()
    assert db.get(Warehouse, source.id) is not None
    assert db.get(Location, loc.id).warehouse_id == source.id


def test_merge_warehouse_source_not_found(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, uuid.uuid4(), wh.id)
    assert exc_info.value.status_code == 404


def test_merge_warehouse_target_not_found(db, seeded):
    wh = create_warehouse(db, seeded.id, "A", "01", "Pharmacy Mainstore Drugs", None, None)
    with pytest.raises(HTTPException) as exc_info:
        merge_warehouse(db, wh.id, uuid.uuid4())
    assert exc_info.value.status_code == 400
