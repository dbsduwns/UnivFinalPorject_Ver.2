"""add password reset security controls

Revision ID: a0b1c2d3e4f5
Revises: 9a1b2c3d4e5f
Create Date: 2026-10-29 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "9a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "password_reset_request_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_request_logs_email_hash", "password_reset_request_logs", ["email_hash"])
    op.create_index("ix_password_reset_request_logs_ip_address", "password_reset_request_logs", ["ip_address"])
    op.create_index("ix_password_reset_request_logs_created_at", "password_reset_request_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_request_logs_created_at", table_name="password_reset_request_logs")
    op.drop_index("ix_password_reset_request_logs_ip_address", table_name="password_reset_request_logs")
    op.drop_index("ix_password_reset_request_logs_email_hash", table_name="password_reset_request_logs")
    op.drop_table("password_reset_request_logs")
    op.drop_column("users", "token_version")
