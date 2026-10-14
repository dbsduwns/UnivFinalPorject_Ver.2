"""add commute profiles

Revision ID: c1a2b3d4e5f6
Revises: e2c4d7a9b031
Create Date: 2026-10-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e2c4d7a9b031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commute_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("home_address", sa.String(length=255), nullable=False),
        sa.Column("home_road_address", sa.String(length=255), nullable=True),
        sa.Column("home_latitude", sa.Float(), nullable=False),
        sa.Column("home_longitude", sa.Float(), nullable=False),
        sa.Column("use_shuttle", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("shuttle_destination", sa.String(length=100), nullable=True),
        sa.Column("departure_buffer_minutes", sa.Integer(), server_default="10", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("commute_profiles")
