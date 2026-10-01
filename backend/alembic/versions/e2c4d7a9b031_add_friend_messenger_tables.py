"""Add direct and group messenger tables.

Revision ID: e2c4d7a9b031
Revises: b6f08c1d4e92
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2c4d7a9b031"
down_revision: Union[str, Sequence[str], None] = "b6f08c1d4e92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_table(name: str, required_columns: set[str], create) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(name):
        create()
        return
    existing_columns = {column["name"] for column in inspector.get_columns(name)}
    missing = required_columns - existing_columns
    if missing:
        raise RuntimeError(f"{name} table already exists but is missing columns: {sorted(missing)}")


def _ensure_index(name: str, table: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _ensure_table(
        "room_messengers",
        {"id", "is_group", "name", "direct_key", "created_at", "updated_at"},
        lambda: op.create_table(
            "room_messengers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("is_group", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=True),
            sa.Column("direct_key", sa.String(length=64), unique=True, nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        ),
    )
    _ensure_table(
        "room_participants",
        {"id", "room_id", "user_id", "last_read"},
        lambda: op.create_table(
            "room_participants",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_id", sa.Integer(), sa.ForeignKey("room_messengers.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("last_read", sa.TIMESTAMP(), server_default=sa.func.now()),
            sa.UniqueConstraint("room_id", "user_id", name="uq_room_participant"),
        ),
    )
    _ensure_index("ix_room_participants_room_id", "room_participants", ["room_id"])
    _ensure_index("ix_room_participants_user_id", "room_participants", ["user_id"])
    _ensure_table(
        "messengers",
        {"id", "room_messenger_id", "sender_id", "content", "created_at", "updated_at"},
        lambda: op.create_table(
            "messengers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_messenger_id", sa.Integer(), sa.ForeignKey("room_messengers.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        ),
    )
    _ensure_index("ix_messengers_room_messenger_id", "messengers", ["room_messenger_id"])
    _ensure_index("ix_messengers_sender_id", "messengers", ["sender_id"])


def downgrade() -> None:
    op.drop_table("messengers")
    op.drop_table("room_participants")
    op.drop_table("room_messengers")
