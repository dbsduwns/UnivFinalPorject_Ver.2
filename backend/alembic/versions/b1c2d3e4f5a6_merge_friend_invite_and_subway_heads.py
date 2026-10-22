"""merge friend invite and subway migration heads

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6, b9c0d1e2f3a4
"""

from typing import Sequence, Union


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = ("a1b2c3d4e5f6", "b9c0d1e2f3a4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
