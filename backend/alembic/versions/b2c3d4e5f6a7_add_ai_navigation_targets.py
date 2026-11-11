"""Store navigation targets on AI assistant messages.

Revision ID: b2c3d4e5f6a7
Revises: a2b3c4d5e6f7
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("messages", sa.Column("navigation_targets", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("messages", "navigation_targets")
