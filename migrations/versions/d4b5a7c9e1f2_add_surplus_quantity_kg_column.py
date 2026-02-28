"""add surplus quantity_kg column

Revision ID: d4b5a7c9e1f2
Revises: c3a91b7d2e10
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "d4b5a7c9e1f2"
down_revision = "c3a91b7d2e10"
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
    if "quantity_kg" not in columns:
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.add_column(sa.Column("quantity_kg", sa.Float(), nullable=True, server_default="0"))

    op.execute("UPDATE surplus SET quantity_kg = COALESCE(quantity, 0) WHERE quantity_kg IS NULL")

    with op.batch_alter_table("surplus") as batch_op:
        batch_op.alter_column("quantity_kg", existing_type=sa.Float(), nullable=False, server_default="0")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "surplus"):
        return

    columns = _column_names(inspector, "surplus")
    if "quantity_kg" in columns:
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.drop_column("quantity_kg")
