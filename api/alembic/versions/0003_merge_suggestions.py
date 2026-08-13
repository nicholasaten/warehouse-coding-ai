"""merge_suggestions, upload_batches.pending_count

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upload_batches", sa.Column("pending_count", sa.Integer(), nullable=False, server_default="0")
    )

    op.create_table(
        "merge_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("upload_batch_id", sa.Uuid(), sa.ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_type_code", sa.String(length=2), nullable=False),
        sa.Column("raw_category_rack", sa.String(length=100), nullable=True),
        sa.Column("raw_description", sa.String(length=500), nullable=False),
        sa.Column("suggested_location_id", sa.Uuid(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_merge_suggestion_status"),
    )


def downgrade() -> None:
    op.drop_table("merge_suggestions")
    op.drop_column("upload_batches", "pending_count")
