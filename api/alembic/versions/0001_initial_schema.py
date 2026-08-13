"""initial schema: sites, coding-formula config tables, warehouses, locations, users

Revision ID: 0001
Revises:
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_code", sa.String(length=5), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code", name="uq_sites_code"),
    )

    op.create_table(
        "warehouse_type_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("code", name="uq_warehouse_type_configs_code"),
    )

    op.create_table(
        "warehouse_code_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("warehouse_type_code", sa.String(length=2), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("warehouse_type_code", "code", name="uq_wh_code_per_type"),
    )

    op.create_table(
        "location_type_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("warehouse_type_code", sa.String(length=2), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_whole_warehouse", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("warehouse_type_code", "code", name="uq_loc_type_per_wh_type"),
    )

    op.create_table(
        "category_rack_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("warehouse_type_code", sa.String(length=2), nullable=False),
        sa.Column("raw_category_text", sa.String(length=100), nullable=False),
        sa.Column(
            "location_type_config_id", sa.Uuid(), sa.ForeignKey("location_type_configs.id"), nullable=False
        ),
        sa.UniqueConstraint("warehouse_type_code", "raw_category_text", name="uq_category_rack_per_wh_type"),
    )

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("warehouse_type_code", sa.String(length=2), nullable=False),
        sa.Column("warehouse_code", sa.String(length=2), nullable=False),
        sa.Column("duplicate_letter", sa.String(length=1), nullable=True),
        sa.Column("generated_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("generated_code", name="uq_warehouses_generated_code"),
        sa.UniqueConstraint(
            "site_id", "warehouse_type_code", "warehouse_code", "duplicate_letter", name="uq_warehouse_formula_key"
        ),
    )
    op.create_index("ix_warehouses_generated_code", "warehouses", ["generated_code"])

    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_type_code", sa.String(length=2), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("generated_code", sa.String(length=40), nullable=False),
        sa.Column("category_rack_raw", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("generated_code", name="uq_locations_generated_code"),
        sa.UniqueConstraint("warehouse_id", "location_type_code", "seq", name="uq_location_formula_key"),
    )
    op.create_index("ix_locations_generated_code", "locations", ["generated_code"])

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("locations")
    op.drop_table("warehouses")
    op.drop_table("category_rack_mappings")
    op.drop_table("location_type_configs")
    op.drop_table("warehouse_code_configs")
    op.drop_table("warehouse_type_configs")
    op.drop_table("sites")
