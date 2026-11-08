from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class CommentReport(Base):
    __tablename__ = "comment_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 계정이나 댓글이 삭제되더라도 관리자 신고 기록은 유지합니다.
    reporter_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reported_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment_id = Column(
        Integer,
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    content_snapshot = Column(Text, nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
    )
    reviewed_at = Column(TIMESTAMP, nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    comment = relationship("Comment", foreign_keys=[comment_id])
    post = relationship("Post", foreign_keys=[post_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        UniqueConstraint(
            "reporter_id",
            "comment_id",
            name="uq_comment_reports_reporter_comment",
        ),
        UniqueConstraint(
            "reporter_id",
            "post_id",
            name="uq_comment_reports_reporter_post",
        ),
        CheckConstraint(
            "reason IN ('abuse', 'hate', 'sexual', 'spam', "
            "'personal_info', 'impersonation', 'illegal', 'other')",
            name="ck_comment_reports_reason",
        ),
        CheckConstraint(
            "status IN ('pending', 'reviewing', 'resolved', 'dismissed')",
            name="ck_comment_reports_status",
        ),
        CheckConstraint(
            "reporter_id IS NULL OR reported_user_id IS NULL "
            "OR reporter_id <> reported_user_id",
            name="ck_comment_reports_not_self",
        ),
        Index("ix_comment_reports_comment_id", "comment_id"),
        Index("ix_comment_reports_post_id", "post_id"),
        Index("ix_comment_reports_status_created_at", "status", "created_at"),
    )
