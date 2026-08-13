"""Loads the company's real, fixed coding-formula config -- extracted
directly from "Formula Warehouse and Location.pptx" and cross-checked
against every row of "RSUS Mapping.xlsx" (see api/tests/test_id_generator_service.py).

This script only ever INSERTS rows that don't already exist (by natural
key) -- it never overwrites an admin's own edits to this config on a
re-run. Run once, after the Alembic migration:

    python -m scripts.seed_config

Sites: only 4 are seeded here because only 4 appear anywhere in the source
material (RSUS, SHMD, SHBP, MRCCC). RSUS/SHMD/SHBP's `short_code` are
confirmed by real Location IDs in the data (RSUS->US, SHMD->MD, SHBP->BP).
MRCCC's is NOT confirmed by any real example in the source files -- seeded
as "CC" (same "drop the leading letters" pattern as the other three) but
flagged here as a guess; verify/correct it via PUT before generating any
real MRCCC location codes.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location_type import LocationTypeConfig
from app.models.site import Site
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig

SITES = [
    # code, name, short_code
    ("RSUS", "Rumah Sakit Umum Siloam", "US"),
    ("SHMD", "Siloam Hospitals Medan", "MD"),
    ("SHBP", "Siloam Hospitals Balikpapan", "BP"),
    ("MRCCC", "Mochtar Riady Comprehensive Cancer Centre", "CC"),  # unconfirmed -- see docstring
]

WAREHOUSE_TYPES = [
    # code, description
    ("A", "Non-General Items"),
    ("B", "General Items"),
    ("C", "Transit"),
]

# (warehouse_type_code, code, description)
WAREHOUSE_CODES_NON_GENERAL = [
    ("A", "01", "Pharmacy Mainstore"),
    ("A", "02", "Pharmacy Outpatient"),
    ("A", "03", "Pharmacy Inpatient"),
    ("A", "04", "Satellite/Ward"),
    ("A", "05", "OPD Clinics"),
    ("A", "06", "Operating Theater"),
    ("A", "07", "CSSD"),
    ("A", "08", "Emergency"),
    ("A", "09", "Critical Care"),
    ("A", "10", "Cath Lab"),
    ("A", "11", "Hemodialysis"),
    ("A", "12", "Laboratory"),
    ("A", "13", "Radiology"),
    ("A", "14", "Medical Check Up"),
    ("A", "15", "Medical Rehab"),
    ("A", "16", "Nutrition & Dietetics"),
    ("A", "17", "Homecare"),
    ("A", "18", "Emergency Trolley"),
]

WAREHOUSE_CODES_GENERAL = [
    ("B", "00", "Management"),
    ("B", "01", "Medical"),
    ("B", "02", "Quality and Nursing"),
    ("B", "03", "Network Operations"),
    ("B", "04", "Information"),
    ("B", "05", "Strategy and Commercial"),
    ("B", "06", "Legal"),
    ("B", "07", "Human Capital"),
    ("B", "08", "Patient Experience"),
    ("B", "09", "Operations Services and SCM"),
    ("B", "10", "Corporate Affairs and Sustainability"),
    ("B", "11", "Go Beyond"),
    ("B", "12", "Ancillary Services and Medical Affair"),
    ("B", "13", "Nursing"),
    ("B", "14", "Business"),
    ("B", "15", "Operations and Services"),
    ("B", "16", "Finance and Administration"),
    ("B", "17", "Casemix"),
    ("B", "18", "FM & GA"),
    ("B", "19", "Quality and Risk"),
    ("B", "20", "ICT"),
    ("B", "21", "Human Capital"),
    ("B", "22", "Hospital Management"),
]

# (warehouse_type_code, code, description, is_whole_warehouse)
LOCATION_TYPES_NON_GENERAL = [
    ("A", "A", "Drugs/Consumables", False),
    ("A", "B", "Cold Storage Items", False),
    ("A", "C", "Trolley", False),
    ("A", "D", "Bag", False),
    ("A", "E", "Expired Items", False),
    ("A", "F", "Bulk", False),
    ("A", "G", "Quarantine", False),
    ("A", "H", "All", True),
]

LOCATION_TYPES_GENERAL = [
    ("B", "A", "Rak", False),
    ("B", "B", "All", True),
]

# (warehouse_type_code, raw_category_text, loc_type_warehouse_type_code, loc_type_code)
# Only the raw "Category Rack" texts actually observed in the real RSUS
# Mapping data are seeded -- deliberately not guessing at unobserved ones
# (e.g. what raw text maps to Non-General's Trolley/Bulk/All), since this
# table is supposed to reflect what's really been seen, not an invented
# complete mapping. Add more via the API as new raw text shows up in future
# uploads.
CATEGORY_RACK_MAPPINGS = [
    ("A", "DRUGS", "A", "A"),
    ("A", "CONSUMABLES", "A", "A"),
    ("A", "COLD STORAGE", "A", "B"),
    ("A", "EXPIRED ITEMS", "A", "E"),
    ("A", "QUARANTINE", "A", "G"),
    ("A", "BAG", "A", "D"),
    ("B", "ALL", "B", "B"),
]


def _get_or_create_site(db: Session, code: str, name: str, short_code: str) -> None:
    if db.scalar(select(Site).where(Site.code == code)):
        return
    db.add(Site(code=code, name=name, short_code=short_code))


def _get_or_create_wh_type(db: Session, code: str, description: str) -> None:
    if db.scalar(select(WarehouseTypeConfig).where(WarehouseTypeConfig.code == code)):
        return
    db.add(WarehouseTypeConfig(code=code, description=description))


def _get_or_create_wh_code(db: Session, wh_type: str, code: str, description: str) -> None:
    exists = db.scalar(
        select(WarehouseCodeConfig).where(
            WarehouseCodeConfig.warehouse_type_code == wh_type, WarehouseCodeConfig.code == code
        )
    )
    if exists:
        return
    db.add(WarehouseCodeConfig(warehouse_type_code=wh_type, code=code, description=description))


def _get_or_create_loc_type(
    db: Session, wh_type: str, code: str, description: str, is_whole_warehouse: bool
) -> LocationTypeConfig:
    existing = db.scalar(
        select(LocationTypeConfig).where(
            LocationTypeConfig.warehouse_type_code == wh_type, LocationTypeConfig.code == code
        )
    )
    if existing:
        return existing
    row = LocationTypeConfig(
        warehouse_type_code=wh_type, code=code, description=description, is_whole_warehouse=is_whole_warehouse
    )
    db.add(row)
    db.flush()
    return row


def main() -> None:
    db = SessionLocal()
    try:
        for code, name, short_code in SITES:
            _get_or_create_site(db, code, name, short_code)

        for code, description in WAREHOUSE_TYPES:
            _get_or_create_wh_type(db, code, description)

        for wh_type, code, description in WAREHOUSE_CODES_NON_GENERAL + WAREHOUSE_CODES_GENERAL:
            _get_or_create_wh_code(db, wh_type, code, description)

        loc_type_lookup: dict[tuple[str, str], LocationTypeConfig] = {}
        for wh_type, code, description, is_whole in LOCATION_TYPES_NON_GENERAL + LOCATION_TYPES_GENERAL:
            row = _get_or_create_loc_type(db, wh_type, code, description, is_whole)
            loc_type_lookup[(wh_type, code)] = row

        for wh_type, raw_text, loc_wh_type, loc_code in CATEGORY_RACK_MAPPINGS:
            exists = db.scalar(
                select(CategoryRackMapping).where(
                    CategoryRackMapping.warehouse_type_code == wh_type,
                    CategoryRackMapping.raw_category_text == raw_text,
                )
            )
            if exists:
                continue
            loc_type = loc_type_lookup[(loc_wh_type, loc_code)]
            db.add(
                CategoryRackMapping(
                    warehouse_type_code=wh_type, raw_category_text=raw_text, location_type_config_id=loc_type.id
                )
            )

        db.commit()
        print("Config seeded (existing rows left untouched).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
