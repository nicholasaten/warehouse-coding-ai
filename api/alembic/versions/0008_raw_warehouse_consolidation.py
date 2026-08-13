"""raw warehouse consolidation

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "raw_warehouse_suggestions",
        sa.Column("consolidated_legacy_names", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("raw_warehouse_suggestions", "consolidated_legacy_names")
