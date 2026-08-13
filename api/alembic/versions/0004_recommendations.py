"""recommendations

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("warehouse_ids", sa.JSON(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "category IN ('merge_opportunity', 'redundant_warehouse', 'underutilized', 'overloaded')",
            name="chk_recommendation_category",
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendations")
