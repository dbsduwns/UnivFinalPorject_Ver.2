"""add menu OCR fields

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("daily_menus", sa.Column("image_sha256", sa.String(64), nullable=True))
    op.add_column(
        "daily_menus",
        sa.Column(
            "ocr_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("daily_menus", sa.Column("ocr_error", sa.Text(), nullable=True))
    op.add_column("menu_items", sa.Column("meal_type", sa.String(30), nullable=True))
    op.add_column("menu_items", sa.Column("corner", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "corner")
    op.drop_column("menu_items", "meal_type")
    op.drop_column("daily_menus", "ocr_error")
    op.drop_column("daily_menus", "ocr_status")
    op.drop_column("daily_menus", "image_sha256")
