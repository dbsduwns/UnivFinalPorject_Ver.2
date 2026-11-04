"""add stable source key to notices

Revision ID: fc1d2e3f4a5b
Revises: fb1c2d3e4f5a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fc1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "fb1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notices",
        sa.Column("source_key", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_notices_source_key", "notices", ["source_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notices_source_key", table_name="notices")
    op.drop_column("notices", "source_key")
