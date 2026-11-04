"""add oauth onboarding and student verification sessions

Revision ID: fb1c2d3e4f5a
Revises: fa0b1c2d3e4f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fb1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "fa0b1c2d3e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_onboarding_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("onboarding_token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "provider IN ('google')",
            name="ck_oauth_onboarding_sessions_provider",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("onboarding_token_hash"),
    )
    op.create_index(
        "ix_oauth_onboarding_sessions_provider_subject",
        "oauth_onboarding_sessions",
        ["provider", "provider_subject"],
    )
    op.create_index(
        "ix_oauth_onboarding_sessions_expires_at",
        "oauth_onboarding_sessions",
        ["expires_at"],
    )

    op.create_table(
        "student_verification_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("onboarding_session_id", sa.Integer(), nullable=False),
        sa.Column("student_email", sa.String(length=320), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ch_student_verification_attempt_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["onboarding_session_id"],
            ["oauth_onboarding_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_student_verification_onboarding_session_id",
        "student_verification_sessions",
        ["onboarding_session_id"],
    )
    op.create_index(
        "ix_student_verification_student_email",
        "student_verification_sessions",
        ["student_email"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_student_verification_student_email",
        table_name="student_verification_sessions",
    )
    op.drop_index(
        "ix_student_verification_onboarding_session_id",
        table_name="student_verification_sessions",
    )
    op.drop_table("student_verification_sessions")
    op.drop_index(
        "ix_oauth_onboarding_sessions_expires_at",
        table_name="oauth_onboarding_sessions",
    )
    op.drop_index(
        "ix_oauth_onboarding_sessions_provider_subject",
        table_name="oauth_onboarding_sessions",
    )
    op.drop_table("oauth_onboarding_sessions")
