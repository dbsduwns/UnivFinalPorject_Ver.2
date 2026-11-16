"""add image metadata to community posts"""

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = ("c3d4e5f6a7b8", "c3e4f5a6b7d8")
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("image_url", sa.String(length=1024), nullable=True))
    op.add_column("posts", sa.Column("image_path", sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column("posts", "image_path")
    op.drop_column("posts", "image_url")
