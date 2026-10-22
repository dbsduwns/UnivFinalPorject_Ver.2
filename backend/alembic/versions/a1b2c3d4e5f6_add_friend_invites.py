"""add revocable one-time friend invite tokens

Revision ID: a1b2c3d4e5f6
Revises: f7a18c2d4e60
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f7a18c2d4e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "friend_invites",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("inviter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_friend_invites_token_hash", "friend_invites", ["token_hash"], unique=True)
    op.create_index("ix_friend_invites_inviter_id", "friend_invites", ["inviter_id"])
    op.create_index("ix_friend_invites_expires_at", "friend_invites", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_friend_invites_expires_at", table_name="friend_invites")
    op.drop_index("ix_friend_invites_inviter_id", table_name="friend_invites")
    op.drop_index("ix_friend_invites_token_hash", table_name="friend_invites")
    op.drop_table("friend_invites")
