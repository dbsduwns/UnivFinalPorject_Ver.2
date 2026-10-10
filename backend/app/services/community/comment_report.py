from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community.comment import Comment
from app.models.community.comment_report import CommentReport
from app.models.user import User
from app.schemas.community.comment_report import (
    CreateCommentReport,
    UpdateCommentReportStatus,
)


def get_comment_reports(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[CommentReport]:
    return (
        db.query(CommentReport)
        .order_by(CommentReport.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_comment_report_by_id(
    db: Session,
    report_id: int,
) -> CommentReport | None:
    return (
        db.query(CommentReport)
        .filter(CommentReport.id == report_id)
        .first()
    )


def create_comment_report(
    db: Session,
    user: User,
    comment_id: int,
    data: CreateCommentReport,
) -> CommentReport:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError("댓글을 찾을 수 없습니다")

    if comment.author_id == user.id:
        raise PermissionError("자신의 댓글은 신고할 수 없습니다")

    if comment.is_hidden:
        raise PermissionError(
            "Comment is hidden. You do not have permission to report"
        )

    existing_report = (
        db.query(CommentReport)
        .filter(
            CommentReport.reporter_id == user.id,
            CommentReport.comment_id == comment_id,
        )
        .first()
    )
    if existing_report is not None:
        raise ValueError("이미 신고한 댓글입니다")

    comment_report = CommentReport(
        reporter_id=user.id,
        reported_user_id=comment.author_id,
        comment_id=comment.id,
        reason=data.reason.value,
        description=data.description,
        content_snapshot=comment.content,
    )

    try:
        db.add(comment_report)
        db.commit()
        db.refresh(comment_report)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 신고한 댓글입니다") from exc

    return comment_report


def update_comment_report_status(
    db: Session,
    admin: User,
    report_id: int,
    data: UpdateCommentReportStatus,
) -> CommentReport:
    report = get_comment_report_by_id(db, report_id)
    if report is None:
        raise LookupError("신고 내역을 찾을 수 없습니다")

    report.status = data.status.value
    report.resolution_note = data.resolution_note
    report.reviewed_by_id = admin.id
    report.reviewed_at = func.now()

    try:
        db.commit()
        db.refresh(report)
    except IntegrityError:
        db.rollback()
        raise

    return report
