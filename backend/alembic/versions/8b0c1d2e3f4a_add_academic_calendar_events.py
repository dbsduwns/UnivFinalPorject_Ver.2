"""add academic calendar events

Revision ID: 8b0c1d2e3f4a
Revises: 7a9d2e4f6b8c
Create Date: 2026-10-27 16:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b0c1d2e3f4a"
down_revision: Union[str, Sequence[str], None] = "7a9d2e4f6b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_calendar_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("source_document", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "academic_year", "title", "start_date", "end_date",
            name="uq_academic_calendar_event_dates",
        ),
    )
    op.create_index("ix_academic_calendar_events_academic_year", "academic_calendar_events", ["academic_year"])
    op.create_index("ix_academic_calendar_events_start_date", "academic_calendar_events", ["start_date"])
    op.create_index("ix_academic_calendar_events_end_date", "academic_calendar_events", ["end_date"])


def downgrade() -> None:
    op.drop_index("ix_academic_calendar_events_end_date", table_name="academic_calendar_events")
    op.drop_index("ix_academic_calendar_events_start_date", table_name="academic_calendar_events")
    op.drop_index("ix_academic_calendar_events_academic_year", table_name="academic_calendar_events")
    op.drop_table("academic_calendar_events")
