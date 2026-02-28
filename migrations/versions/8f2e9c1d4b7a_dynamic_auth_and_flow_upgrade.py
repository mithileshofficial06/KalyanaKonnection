"""dynamic auth and flow upgrade

Revision ID: 8f2e9c1d4b7a
Revises: 112284e3a8d5
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "8f2e9c1d4b7a"
down_revision = "112284e3a8d5"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_names(inspector, table_name):
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        user_cols = _column_names(inspector, "users")
        with op.batch_alter_table("users") as batch_op:
            if "phone_number" not in user_cols:
                batch_op.add_column(sa.Column("phone_number", sa.String(length=20), nullable=True))
            if "phone_verified" not in user_cols:
                batch_op.add_column(sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))

        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone_number ON users (phone_number)")

    if not _table_exists(inspector, "events"):
        op.create_table(
            "events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("event_name", sa.String(length=150), nullable=False),
            sa.Column("event_date", sa.DateTime(), nullable=False),
            sa.Column("guest_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _table_exists(inspector, "surplus"):
        op.create_table(
            "surplus",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True),
            sa.Column("event_name", sa.String(length=150), nullable=False),
            sa.Column("provider_name", sa.String(length=120), nullable=False),
            sa.Column("food_type", sa.String(length=150), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("estimated_expiry", sa.String(length=80), nullable=True),
            sa.Column("distance_km", sa.Float(), nullable=True),
            sa.Column("photo_path", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="available"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    else:
        surplus_cols = _column_names(inspector, "surplus")
        with op.batch_alter_table("surplus") as batch_op:
            if "provider_id" not in surplus_cols:
                batch_op.add_column(sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
            if "event_id" not in surplus_cols:
                batch_op.add_column(sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True))
            if "quantity" not in surplus_cols:
                batch_op.add_column(sa.Column("quantity", sa.Float(), nullable=True))
            if "status" in surplus_cols:
                pass
        if "quantity" not in surplus_cols and "quantity_kg" in surplus_cols:
            op.execute("UPDATE surplus SET quantity = quantity_kg WHERE quantity IS NULL")

    if not _table_exists(inspector, "allocations"):
        op.create_table(
            "allocations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("surplus_id", sa.Integer(), sa.ForeignKey("surplus.id"), nullable=False),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("ngo_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="requested"),
            sa.Column("pickup_time", sa.DateTime(), nullable=True),
            sa.Column("otp_code", sa.String(length=6), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _table_exists(inspector, "reviews"):
        op.create_table(
            "reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ngo_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _table_exists(inspector, "complaints"):
        op.create_table(
            "complaints",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ngo_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("issue_type", sa.String(length=80), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Under Review"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_users_phone_number")

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ["complaints", "reviews", "allocations", "surplus", "events"]:
        if _table_exists(inspector, table_name):
            op.drop_table(table_name)

    if _table_exists(inspector, "users"):
        user_cols = _column_names(inspector, "users")
        with op.batch_alter_table("users") as batch_op:
            if "phone_verified" in user_cols:
                batch_op.drop_column("phone_verified")
            if "phone_number" in user_cols:
                batch_op.drop_column("phone_number")
