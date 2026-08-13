"""Produces a Warehouse Master + Location Master .xlsx for one Hospital
Unit (Site), in the EXACT column format excel_ingest_service's upload
endpoints already require -- so the same file that comes out of this
export can be handed back to the Uploads page unchanged and re-ingested,
no reformatting. Two sheets in one workbook, not two separate files,
since that's simpler for an admin to keep track of per hospital.

Adds one extra "Generated Code" column at the end of each sheet, purely
informational -- the importer only requires the columns it already
checks for (see excel_ingest_service._require_columns), so an extra
column is silently ignored on re-upload, not a round-trip hazard."""
import io
import uuid

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.site import Site
from app.models.warehouse import Warehouse


def export_site_master(db: Session, site_id: uuid.UUID) -> tuple[bytes, str]:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    warehouses = list(
        db.scalars(select(Warehouse).where(Warehouse.site_id == site_id).order_by(Warehouse.generated_code)).all()
    )
    warehouse_ids = [w.id for w in warehouses]
    locations = (
        list(
            db.scalars(
                select(Location).where(Location.warehouse_id.in_(warehouse_ids)).order_by(Location.generated_code)
            ).all()
        )
        if warehouse_ids
        else []
    )
    warehouse_by_id = {w.id: w for w in warehouses}

    workbook = openpyxl.Workbook()

    wh_sheet = workbook.active
    wh_sheet.title = "Warehouse Master"
    wh_sheet.append(
        ["Site Code", "Warehouse Type Code", "Warehouse Code", "Warehouse Name", "Description", "Capacity", "Generated Code"]
    )
    for warehouse in warehouses:
        wh_sheet.append(
            [
                site.code,
                warehouse.warehouse_type_code,
                warehouse.warehouse_code,
                warehouse.name,
                warehouse.description or "",
                warehouse.capacity if warehouse.capacity is not None else "",
                warehouse.generated_code,
            ]
        )

    loc_sheet = workbook.create_sheet("Location Master")
    loc_sheet.append(["Warehouse Code", "Category Rack", "Description", "Generated Code"])
    for location in locations:
        warehouse = warehouse_by_id[location.warehouse_id]
        loc_sheet.append(
            [warehouse.generated_code, location.category_rack_raw or "", location.description, location.generated_code]
        )

    buffer = io.BytesIO()
    workbook.save(buffer)
    filename = f"{site.code}-master-export.xlsx"
    return buffer.getvalue(), filename
