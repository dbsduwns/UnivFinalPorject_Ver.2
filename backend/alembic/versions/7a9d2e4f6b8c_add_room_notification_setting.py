"""add per-room notification setting

Revision ID: 7a9d2e4f6b8c
Revises: 6e8b1f2c3d4a
Create Date: 2026-10-27 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a9d2e4f6b8c"
down_revision: Union[str, Sequence[str], None] = "6e8b1f2c3d4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "room_participants",
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("room_participants", "is_muted")
