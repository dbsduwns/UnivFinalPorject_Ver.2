"""make subject codes unique per semester

Revision ID: b6f08c1d4e92
Revises: 0c16a9230157
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6f08c1d4e92"
down_revision: Union[str, Sequence[str], None] = "0c16a9230157"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL assigns this default name to the unnamed unique constraint in
    # the initial migration.  The constraint must be removed before a course
    # code can appear once for each semester.
    op.drop_constraint("subjects_subject_code_key", "subjects", type_="unique")
    op.create_unique_constraint(
        "uq_subjects_subject_code_semester",
        "subjects",
        ["subject_code", "semester"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_subjects_subject_code_semester", "subjects", type_="unique")
    op.create_unique_constraint("subjects_subject_code_key", "subjects", ["subject_code"])
