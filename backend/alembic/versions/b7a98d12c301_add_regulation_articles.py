"""Add regulation articles for official university rules.

Revision ID: b7a98d12c301
Revises: 0aac2d5fc542
"""

from alembic import op
import sqlalchemy as sa


revision = "b7a98d12c301"
down_revision = "0aac2d5fc542"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regulation_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("rule_title", sa.String(length=300), nullable=False),
        sa.Column("article_heading", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_key", name="uq_regulation_articles_source_key"),
    )
    op.create_index("ix_regulation_articles_rule_title", "regulation_articles", ["rule_title"])


def downgrade() -> None:
    op.drop_index("ix_regulation_articles_rule_title", table_name="regulation_articles")
    op.drop_table("regulation_articles")
