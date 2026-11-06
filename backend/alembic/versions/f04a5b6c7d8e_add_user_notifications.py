"""add user notification center

Revision ID: f04a5b6c7d8e
Revises: fe3f4a5b6c7d
"""

from alembic import op
import sqlalchemy as sa


revision = "f04a5b6c7d8e"
down_revision = "fe3f4a5b6c7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
    op.create_index("ix_user_notifications_notification_type", "user_notifications", ["notification_type"])
    op.create_index("ix_user_notifications_created_at", "user_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_notifications_created_at", table_name="user_notifications")
    op.drop_index("ix_user_notifications_notification_type", table_name="user_notifications")
    op.drop_index("ix_user_notifications_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
