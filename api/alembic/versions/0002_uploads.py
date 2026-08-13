"""upload_batches, upload_errors

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "file_type IN ('warehouse_master', 'location_master')", name="chk_upload_batch_file_type"
        ),
        sa.CheckConstraint("status IN ('processing', 'completed', 'failed')", name="chk_upload_batch_status"),
    )

    op.create_table(
        "upload_errors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("upload_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(length=100), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("upload_errors")
    op.drop_table("upload_batches")
