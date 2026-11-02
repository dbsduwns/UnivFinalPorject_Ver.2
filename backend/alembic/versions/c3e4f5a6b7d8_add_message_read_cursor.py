"""Track the last read message ID for accurate per-message unread counts.

Revision ID: c3e4f5a6b7d8
Revises: b7a98d12c301
"""

from alembic import op
import sqlalchemy as sa


revision = "c3e4f5a6b7d8"
down_revision = "b7a98d12c301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("room_participants", sa.Column("last_read_message_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE room_participants AS participant
        SET last_read_message_id = (
            SELECT MAX(message.id)
            FROM messengers AS message
            WHERE message.room_messenger_id = participant.room_id
              AND message.created_at <= participant.last_read
        )
        """
    )


def downgrade() -> None:
    op.drop_column("room_participants", "last_read_message_id")
