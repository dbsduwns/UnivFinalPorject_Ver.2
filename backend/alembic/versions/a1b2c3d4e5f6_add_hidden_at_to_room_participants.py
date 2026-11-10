"""Hide direct chat rooms per participant when a friendship is removed.

Revision ID: a2b3c4d5e6f7
Revises: ff1a2b3c4d5e
"""

from alembic import op
import sqlalchemy as sa


revision = "a2b3c4d5e6f7"
down_revision = "ff1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("room_participants", sa.Column("hidden_at", sa.TIMESTAMP(), nullable=True))


def downgrade():
    op.drop_column("room_participants", "hidden_at")
