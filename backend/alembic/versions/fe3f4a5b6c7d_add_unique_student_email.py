"""add unique student email to users

Revision ID: fe3f4a5b6c7d
Revises: fd2e3f4a5b6c
"""

from alembic import op
import sqlalchemy as sa


revision = "fe3f4a5b6c7d"
down_revision = "fd2e3f4a5b6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("student_email", sa.String(length=320), nullable=True))
    op.create_unique_constraint("uq_users_student_email", "users", ["student_email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_student_email", "users", type_="unique")
    op.drop_column("users", "student_email")
