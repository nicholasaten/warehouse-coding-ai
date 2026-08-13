"""raw import

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_import_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "raw_warehouse_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("raw_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("legacy_code", sa.String(length=50), nullable=False),
        sa.Column("legacy_name", sa.String(length=255), nullable=False),
        sa.Column("raw_rows", sa.JSON(), nullable=False),
        sa.Column("suggested_warehouse_type_code", sa.String(length=2), nullable=True),
        sa.Column("suggested_warehouse_code", sa.String(length=2), nullable=True),
        sa.Column("reasoning", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_raw_wh_suggestion_status"),
    )

    op.create_table(
        "raw_location_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("raw_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "warehouse_suggestion_id",
            sa.Uuid(),
            sa.ForeignKey("raw_warehouse_suggestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("legacy_code", sa.String(length=50), nullable=True),
        sa.Column("legacy_description", sa.String(length=500), nullable=False),
        sa.Column("is_active_raw", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("suggested_category_rack", sa.String(length=100), nullable=True),
        sa.Column("reasoning", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_location_id", sa.Uuid(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("created_merge_suggestion_id", sa.Uuid(), sa.ForeignKey("merge_suggestions.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_raw_loc_suggestion_status"),
    )


def downgrade() -> None:
    op.drop_table("raw_location_suggestions")
    op.drop_table("raw_warehouse_suggestions")
    op.drop_table("raw_import_batches")
