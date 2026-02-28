"""normalize user phone numbers and ensure uniqueness

Revision ID: f9a4c2d8b1e6
Revises: e7c2f9a1b6d3
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "f9a4c2d8b1e6"
down_revision = "e7c2f9a1b6d3"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_names(inspector, table_name):
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    columns = _column_names(inspector, "users")
    if "phone_number" not in columns:
        return

    bind.execute(sa.text("DROP INDEX IF EXISTS uq_users_phone_number"))
    bind.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_phone_number_key"))

    rows = bind.execute(sa.text("SELECT id, phone_number FROM users ORDER BY id")).fetchall()

    seen = set()
    for row in rows:
        user_id, phone = row[0], (row[1] or "").strip()

        normalized = None
        if phone:
            digits = "".join(ch for ch in phone if ch.isdigit())
            if len(digits) >= 10:
                candidate = digits[-10:]
                if candidate not in seen:
                    normalized = candidate

        if normalized:
            seen.add(normalized)
        bind.execute(sa.text("UPDATE users SET phone_number=:phone WHERE id=:id"), {"phone": normalized, "id": user_id})

    bind.execute(sa.text("DROP INDEX IF EXISTS uq_users_phone_number"))
    bind.execute(sa.text("CREATE UNIQUE INDEX uq_users_phone_number ON users (phone_number) WHERE phone_number IS NOT NULL"))


def downgrade():
    bind = op.get_bind()
    bind.execute(sa.text("DROP INDEX IF EXISTS uq_users_phone_number"))
    bind.execute(sa.text("CREATE UNIQUE INDEX uq_users_phone_number ON users (phone_number) WHERE phone_number IS NOT NULL"))
