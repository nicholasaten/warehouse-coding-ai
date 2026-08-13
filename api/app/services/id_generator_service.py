"""Deterministic implementation of the company's fixed Warehouse ID / Location
ID coding formulas -- confirmed against the real "Formula Warehouse and
Location.pptx" and, more importantly, against every row of the real
"RSUS Mapping.xlsx" example (see api/tests/test_id_generator_service.py,
which asserts against literal values copied from that file).

This module NEVER invents or modifies the formula itself -- it only applies
whatever WarehouseTypeConfig/WarehouseCodeConfig/LocationTypeConfig/Site
records an admin has configured. Nothing here should ever hardcode a real
site code, warehouse code, or location type -- those all come from the
config tables (or, for the pure functions below, from their caller).

Confirmed formula shapes:
  Warehouse ID = {site_code}-{warehouse_type_code}{warehouse_code}[{duplicate_letter}]
    e.g. "RSUS-A01A", "RSUS-A02" (no duplicate_letter -- only one warehouse
    exists for that site+type+code combination).

  Location ID  = {site_short_code}{warehouse_type_code}{warehouse_code}
                 [{duplicate_letter}]-{location_type_code}[{seq:02d}]
    e.g. "USA01A-A05". Note there is NO hyphen between the short site code
    and the warehouse portion -- only before the final sequence.

    The trailing seq is entirely OMITTED for a "whole warehouse" location
    type (LocationTypeConfig.is_whole_warehouse) -- confirmed by real data:
    General Items warehouses whose only location is Category Rack "ALL"
    (LocType B under the General scheme) produce codes like "USB12-B", not
    "USB12-B01". There is at most one such location per warehouse, so
    there's nothing to number.
"""

from string import ascii_uppercase

STAGING_RECEIVE_SEQ = 99


def format_warehouse_code(
    site_code: str, warehouse_type_code: str, warehouse_code: str, duplicate_letter: str | None
) -> str:
    suffix = duplicate_letter or ""
    return f"{site_code}-{warehouse_type_code}{warehouse_code}{suffix}"


def format_location_code(
    site_short_code: str,
    warehouse_type_code: str,
    warehouse_code: str,
    warehouse_duplicate_letter: str | None,
    location_type_code: str,
    seq: int | None,
) -> str:
    """`seq=None` means this is a "whole warehouse" location type (see
    module docstring) -- the trailing sequence digits are omitted entirely,
    not zero-padded to "00"."""
    wh_suffix = warehouse_duplicate_letter or ""
    seq_suffix = f"{seq:02d}" if seq is not None else ""
    return f"{site_short_code}{warehouse_type_code}{warehouse_code}{wh_suffix}-{location_type_code}{seq_suffix}"


def assign_duplicate_letters(count: int) -> list[str | None]:
    """Given N warehouses that share the same (site, warehouse_type_code,
    warehouse_code), returns the duplicate_letter each should have, in the
    same order. A lone warehouse gets None (no suffix at all -- confirmed by
    the real "RSUS-A02" example, which has no other warehouse under
    type A / code 02). As soon as a second one exists, EVERY warehouse in
    the group gets a letter starting from A -- confirmed by "RSUS-A01A" /
    "RSUS-A01B" both being lettered, not just the second one. This means
    adding a new warehouse to a previously-lone group is expected to also
    rename the existing one's generated_code -- callers must handle that,
    not just assign a letter to the newest row.
    """
    if count <= 0:
        return []
    if count == 1:
        return [None]
    if count > len(ascii_uppercase):
        raise ValueError(f"Cannot assign duplicate letters for {count} warehouses -- only 26 letters available")
    return list(ascii_uppercase[:count])


def next_location_sequence(existing_seqs: list[int], is_staging_receive: bool) -> int:
    """The next seq to assign for a new distinct location within one
    (warehouse, location_type_code) group. STAGING_RECEIVE_SEQ (99) is a
    fixed reserved bucket -- confirmed by the real data, where unrelated
    uncategorized racks always collapsed into one "STAGING RECEIVE" location
    at seq 99 per warehouse, never renumbered into the normal sequence.
    Every other distinct location gets the next integer after whatever's
    already used, starting at 1.
    """
    if is_staging_receive:
        return STAGING_RECEIVE_SEQ
    normal_seqs = [s for s in existing_seqs if s != STAGING_RECEIVE_SEQ]
    return (max(normal_seqs) + 1) if normal_seqs else 1
