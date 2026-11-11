"""Add server-side biometric session state and credentials.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "refresh_sessions",
        sa.Column("biometric_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "refresh_sessions",
        sa.Column("biometric_locked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "refresh_sessions",
        sa.Column("last_biometric_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "refresh_sessions",
        sa.Column("auth_level", sa.String(length=20), server_default="standard", nullable=False),
    )
    op.create_table(
        "biometric_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_session_id", sa.String(length=64), nullable=True),
        sa.Column("credential_hash", sa.String(length=64), nullable=False),
        sa.Column("device_id_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["refresh_session_id"], ["refresh_sessions.session_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_hash"),
        sa.UniqueConstraint("refresh_session_id"),
    )
    op.create_index("ix_biometric_credentials_user_id", "biometric_credentials", ["user_id"])
    op.create_index("ix_biometric_credentials_refresh_session_id", "biometric_credentials", ["refresh_session_id"])
    op.create_index("ix_biometric_credentials_credential_hash", "biometric_credentials", ["credential_hash"])
    op.create_index("ix_biometric_credentials_device_id_hash", "biometric_credentials", ["device_id_hash"])


def downgrade():
    op.drop_index("ix_biometric_credentials_device_id_hash", table_name="biometric_credentials")
    op.drop_index("ix_biometric_credentials_credential_hash", table_name="biometric_credentials")
    op.drop_index("ix_biometric_credentials_refresh_session_id", table_name="biometric_credentials")
    op.drop_index("ix_biometric_credentials_user_id", table_name="biometric_credentials")
    op.drop_table("biometric_credentials")
    op.drop_column("refresh_sessions", "auth_level")
    op.drop_column("refresh_sessions", "last_biometric_at")
    op.drop_column("refresh_sessions", "biometric_locked_at")
    op.drop_column("refresh_sessions", "biometric_enabled")
