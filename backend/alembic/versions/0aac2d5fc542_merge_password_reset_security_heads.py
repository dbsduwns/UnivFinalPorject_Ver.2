"""merge password reset security heads

Revision ID: 0aac2d5fc542
Revises: a0b1c2d3e4f5, 8b0c1d2e3f4a
Create Date: 2026-10-29 13:05:26.392340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0aac2d5fc542'
down_revision: Union[str, Sequence[str], None] = ('a0b1c2d3e4f5', '8b0c1d2e3f4a',)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
