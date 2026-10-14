"""add shuttle map tables

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-10-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shuttle_map_routes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("route_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shuttle_map_stops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stop_name", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shuttle_map_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.String(length=3), nullable=False),
        sa.Column("departure_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["shuttle_map_routes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "route_id",
            "day_of_week",
            "departure_time",
            name="uq_shuttle_map_schedule_departure",
        ),
    )
    op.create_index(
        "ix_shuttle_map_schedules_route_id",
        "shuttle_map_schedules",
        ["route_id"],
    )
    op.create_index(
        "ix_shuttle_map_schedules_day_of_week",
        "shuttle_map_schedules",
        ["day_of_week"],
    )

    op.create_table(
        "shuttle_map_schedule_stops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("stop_id", sa.Integer(), nullable=False),
        sa.Column("arrival_time", sa.Time(), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["shuttle_map_schedules.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stop_id"],
            ["shuttle_map_stops.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "schedule_id",
            "stop_id",
            name="uq_shuttle_map_schedule_stop",
        ),
        sa.UniqueConstraint(
            "schedule_id",
            "stop_order",
            name="uq_shuttle_map_schedule_stop_order",
        ),
    )
    op.create_index(
        "ix_shuttle_map_schedule_stops_schedule_id",
        "shuttle_map_schedule_stops",
        ["schedule_id"],
    )
    op.create_index(
        "ix_shuttle_map_schedule_stops_stop_id",
        "shuttle_map_schedule_stops",
        ["stop_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shuttle_map_schedule_stops_stop_id",
        table_name="shuttle_map_schedule_stops",
    )
    op.drop_index(
        "ix_shuttle_map_schedule_stops_schedule_id",
        table_name="shuttle_map_schedule_stops",
    )
    op.drop_table("shuttle_map_schedule_stops")
    op.drop_index(
        "ix_shuttle_map_schedules_day_of_week",
        table_name="shuttle_map_schedules",
    )
    op.drop_index(
        "ix_shuttle_map_schedules_route_id",
        table_name="shuttle_map_schedules",
    )
    op.drop_table("shuttle_map_schedules")
    op.drop_table("shuttle_map_stops")
    op.drop_table("shuttle_map_routes")
