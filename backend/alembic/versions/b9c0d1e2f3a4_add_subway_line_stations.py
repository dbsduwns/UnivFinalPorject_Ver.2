"""add subway line station cache

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subway_line_stations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("line_name", sa.String(length=50), nullable=False),
        sa.Column("station_code", sa.String(length=50), nullable=False),
        sa.Column("station_name", sa.String(length=120), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("line_name", "station_code", "stop_order", name="uq_subway_line_station_order"),
    )
    op.create_index("ix_subway_line_stations_line_name", "subway_line_stations", ["line_name"])


def downgrade() -> None:
    op.drop_index("ix_subway_line_stations_line_name", table_name="subway_line_stations")
    op.drop_table("subway_line_stations")
