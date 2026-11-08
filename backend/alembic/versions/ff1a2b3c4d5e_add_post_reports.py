"""allow community reports and blocks to target posts"""

from alembic import op
import sqlalchemy as sa


revision = "ff1a2b3c4d5e"
down_revision = ("f15b6c7d8e9f", "fe3f4a5b6c7d")
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "comment_reports",
        sa.Column("post_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_comment_reports_post_id_posts",
        "comment_reports",
        "posts",
        ["post_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_comment_reports_reporter_post",
        "comment_reports",
        ["reporter_id", "post_id"],
    )
    op.create_index(
        "ix_comment_reports_post_id",
        "comment_reports",
        ["post_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_comment_reports_post_id", table_name="comment_reports")
    op.drop_constraint(
        "uq_comment_reports_reporter_post",
        "comment_reports",
        type_="unique",
    )
    op.drop_constraint(
        "fk_comment_reports_post_id_posts",
        "comment_reports",
        type_="foreignkey",
    )
    op.drop_column("comment_reports", "post_id")
