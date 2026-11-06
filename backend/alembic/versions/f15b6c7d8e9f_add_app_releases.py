"""add app release version management

Revision ID: f15b6c7d8e9f
Revises: f04a5b6c7d8e
"""

from alembic import op
import sqlalchemy as sa


revision = "f15b6c7d8e9f"
down_revision = "f04a5b6c7d8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("version_code", sa.Integer(), nullable=False),
        sa.Column("version_name", sa.String(length=50), nullable=False),
        sa.Column("minimum_version_code", sa.Integer(), server_default="1", nullable=False),
        sa.Column("apk_url", sa.String(length=2048), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("release_notes", sa.JSON(), nullable=False),
        sa.Column("mandatory", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "version_code", name="uq_app_releases_platform_version_code"),
    )
    op.create_index("ix_app_releases_platform", "app_releases", ["platform"])
    op.create_index("ix_app_releases_is_active", "app_releases", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_app_releases_is_active", table_name="app_releases")
    op.drop_index("ix_app_releases_platform", table_name="app_releases")
    op.drop_table("app_releases")
