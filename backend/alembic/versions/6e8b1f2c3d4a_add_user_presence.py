"""add user presence for direct-message notification suppression

Revision ID: 6e8b1f2c3d4a
Revises: 4f7a9c2d1e3b
Create Date: 2026-10-27 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e8b1f2c3d4a"
down_revision: Union[str, Sequence[str], None] = "4f7a9c2d1e3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_presences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("active_room_id", sa.Integer(), nullable=True),
        sa.Column("is_app_foreground", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["active_room_id"], ["room_messengers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_presences_user_id", "user_presences", ["user_id"])
    op.create_index("ix_user_presences_active_room_id", "user_presences", ["active_room_id"])
    op.create_index("ix_user_presences_last_seen_at", "user_presences", ["last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_user_presences_last_seen_at", table_name="user_presences")
    op.drop_index("ix_user_presences_active_room_id", table_name="user_presences")
    op.drop_index("ix_user_presences_user_id", table_name="user_presences")
    op.drop_table("user_presences")
