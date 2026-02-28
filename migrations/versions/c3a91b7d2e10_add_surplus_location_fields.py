"""add surplus location fields

Revision ID: c3a91b7d2e10
Revises: 8f2e9c1d4b7a
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "c3a91b7d2e10"
down_revision = "8f2e9c1d4b7a"
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
    with op.batch_alter_table("surplus") as batch_op:
        if "provider_location" not in columns:
            batch_op.add_column(sa.Column("provider_location", sa.String(length=180), nullable=True))
        if "provider_latitude" not in columns:
            batch_op.add_column(sa.Column("provider_latitude", sa.Float(), nullable=True))
        if "provider_longitude" not in columns:
            batch_op.add_column(sa.Column("provider_longitude", sa.Float(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "surplus"):
        return

    columns = _column_names(inspector, "surplus")
    with op.batch_alter_table("surplus") as batch_op:
        if "provider_longitude" in columns:
            batch_op.drop_column("provider_longitude")
        if "provider_latitude" in columns:
            batch_op.drop_column("provider_latitude")
        if "provider_location" in columns:
            batch_op.drop_column("provider_location")
