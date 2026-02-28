"""add mahal_name to surplus

Revision ID: e7c2f9a1b6d3
Revises: d4b5a7c9e1f2
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "e7c2f9a1b6d3"
down_revision = "d4b5a7c9e1f2"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_names(inspector, table_name):
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "surplus"):
        return

    columns = _column_names(inspector, "surplus")
    if "mahal_name" not in columns:
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.add_column(sa.Column("mahal_name", sa.String(length=160), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "surplus"):
        return

    columns = _column_names(inspector, "surplus")
    if "mahal_name" in columns:
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.drop_column("mahal_name")
