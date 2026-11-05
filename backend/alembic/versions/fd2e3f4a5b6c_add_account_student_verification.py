"""add account student verification support

Revision ID: fd2e3f4a5b6c
Revises: fc1d2e3f4a5b
"""

from alembic import op
import sqlalchemy as sa


revision = "fd2e3f4a5b6c"
down_revision = "fc1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("student_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.alter_column(
        "student_verification_sessions",
        "onboarding_session_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "student_verification_sessions",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_student_verification_sessions_user_id",
        "student_verification_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ch_student_verification_owner_required",
        "student_verification_sessions",
        "(onboarding_session_id IS NOT NULL) OR (user_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ch_student_verification_owner_required",
        "student_verification_sessions",
        type_="check",
    )
    op.drop_constraint(
        "fk_student_verification_sessions_user_id",
        "student_verification_sessions",
        type_="foreignkey",
    )
    op.drop_column("student_verification_sessions", "user_id")
    op.alter_column(
        "student_verification_sessions",
        "onboarding_session_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("users", "student_verified_at")
