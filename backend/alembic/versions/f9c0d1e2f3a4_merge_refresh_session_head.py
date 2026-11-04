"""merge refresh session and messaging migration heads

Revision ID: f9c0d1e2f3a4
Revises: c3e4f5a6b7d8, f8b9c0d1e2f3
"""

from typing import Sequence, Union


revision: str = "f9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = (
    "c3e4f5a6b7d8",
    "f8b9c0d1e2f3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
