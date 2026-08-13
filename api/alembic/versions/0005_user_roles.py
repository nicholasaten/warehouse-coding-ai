"""users.role, users.site_id -- admin/pic multi-role for the review workflow

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=10), nullable=False, server_default="admin"))
    op.add_column("users", sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id"), nullable=True))
    op.create_check_constraint(
        "chk_user_role_site_id",
        "users",
        "(role = 'admin' AND site_id IS NULL) OR (role = 'pic' AND site_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("chk_user_role_site_id", "users", type_="check")
    op.drop_column("users", "site_id")
    op.drop_column("users", "role")
