"""PIC acknowledgment tracking for Warehouse/Location

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-14

Requested directly: whenever an admin creates or edits a Warehouse or
Location, the PIC for that Hospital Unit should see it on their own
dashboard and explicitly confirm they've reviewed and agree with the
current coding -- separate from (and the reverse direction of) the
existing PIC-submits-a-Revision workflow. NULL means "not yet reviewed";
both columns are cleared back to NULL by any subsequent edit (see
_apply_value in revision_service.py and the admin PATCH endpoints), since
an acknowledgment only means something if the coding hasn't changed
since.
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("warehouses", sa.Column("pic_acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("warehouses", sa.Column("pic_acknowledged_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "warehouses_pic_acknowledged_by_fkey", "warehouses", "users", ["pic_acknowledged_by"], ["id"], ondelete="SET NULL"
    )

    op.add_column("locations", sa.Column("pic_acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("locations", sa.Column("pic_acknowledged_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "locations_pic_acknowledged_by_fkey", "locations", "users", ["pic_acknowledged_by"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("locations_pic_acknowledged_by_fkey", "locations", type_="foreignkey")
    op.drop_column("locations", "pic_acknowledged_by")
    op.drop_column("locations", "pic_acknowledged_at")

    op.drop_constraint("warehouses_pic_acknowledged_by_fkey", "warehouses", type_="foreignkey")
    op.drop_column("warehouses", "pic_acknowledged_by")
    op.drop_column("warehouses", "pic_acknowledged_at")
