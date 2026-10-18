"""Add community post visibility and pinning.

Revision ID: a8b9c0d1e2f3
Revises: f7a18c2d4e60
"""
from alembic import op
import sqlalchemy as sa

revision = "a8b9c0d1e2f3"
down_revision = "f7a18c2d4e60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("posts", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("posts", "is_pinned")
    op.drop_column("posts", "is_hidden")
