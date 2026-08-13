"""revisions

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("original_value", sa.JSON(), nullable=False),
        sa.Column("proposed_value", sa.JSON(), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=1000), nullable=True),
        sa.Column("final_value", sa.JSON(), nullable=True),
        sa.CheckConstraint("entity_type IN ('warehouse', 'location')", name="chk_revision_entity_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_revision_status"),
    )


def downgrade() -> None:
    op.drop_table("revisions")
