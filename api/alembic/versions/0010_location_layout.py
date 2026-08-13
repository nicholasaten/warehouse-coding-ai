"""location layout fields for the warehouse floor-plan canvas

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13

Free-form position/size for each Location on the per-Warehouse visual
Layout canvas. Purely a display concern -- never read by
id_generator_service or any formula/code-generation logic. All four
columns are nullable: NULL means "not yet placed," and the frontend
auto-arranges those into a grid on first load rather than stacking them
at 0,0.
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("layout_x", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("layout_y", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("layout_width", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("layout_height", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("locations", "layout_height")
    op.drop_column("locations", "layout_width")
    op.drop_column("locations", "layout_y")
    op.drop_column("locations", "layout_x")
