"""delete cascade fixes for raw-import audit trail

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-11

Admin needs to be able to delete a Warehouse/Location outright (not just
deactivate it), and that must not fail with a foreign-key violation or
silently destroy the raw-import AI-suggestion audit trail:
- `raw_warehouse_suggestions.created_warehouse_id` -> SET NULL: the
  suggestion row (who suggested what, when, admin's decision) survives:
  it just no longer points at a live warehouse.
- `raw_location_suggestions.created_location_id` -> SET NULL: same
  reasoning, for the location-level suggestions.
- `raw_location_suggestions.warehouse_id` -> CASCADE: this column is
  NOT NULL (every location suggestion is scoped to a warehouse), so it
  can't be nulled out -- when the warehouse goes, its location-suggestion
  rows go with it, consistent with `warehouse_suggestion_id` already
  cascading the same way.
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("raw_warehouse_suggestions_created_warehouse_id_fkey", "raw_warehouse_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_warehouse_suggestions_created_warehouse_id_fkey",
        "raw_warehouse_suggestions", "warehouses", ["created_warehouse_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("raw_location_suggestions_created_location_id_fkey", "raw_location_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_location_suggestions_created_location_id_fkey",
        "raw_location_suggestions", "locations", ["created_location_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("raw_location_suggestions_warehouse_id_fkey", "raw_location_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_location_suggestions_warehouse_id_fkey",
        "raw_location_suggestions", "warehouses", ["warehouse_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("raw_location_suggestions_warehouse_id_fkey", "raw_location_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_location_suggestions_warehouse_id_fkey", "raw_location_suggestions", "warehouses", ["warehouse_id"], ["id"],
    )

    op.drop_constraint("raw_location_suggestions_created_location_id_fkey", "raw_location_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_location_suggestions_created_location_id_fkey",
        "raw_location_suggestions", "locations", ["created_location_id"], ["id"],
    )

    op.drop_constraint("raw_warehouse_suggestions_created_warehouse_id_fkey", "raw_warehouse_suggestions", type_="foreignkey")
    op.create_foreign_key(
        "raw_warehouse_suggestions_created_warehouse_id_fkey",
        "raw_warehouse_suggestions", "warehouses", ["created_warehouse_id"], ["id"],
    )
