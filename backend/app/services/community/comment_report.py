from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community.comment import Comment
from app.models.community.comment_report import CommentReport
from app.models.community.post import Post
from app.models.user import User
from app.schemas.community.comment_report import (
    CreateCommentReport,
    CreatePostReport,
    UpdateCommentReportStatus,
)


def get_comment_reports(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[CommentReport]:
    reports = (
        db.query(CommentReport)
        .order_by(CommentReport.created_at.desc(), CommentReport.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return enrich_reports(db, reports)


def get_comment_report_by_id(
    db: Session,
    report_id: int,
) -> CommentReport | None:
    report = (
        db.query(CommentReport)
        .filter(CommentReport.id == report_id)
        .first()
    )
    return enrich_reports(db, [report])[0] if report else None


def enrich_reports(db: Session, reports: list[CommentReport]) -> list[CommentReport]:
    ids = {report.comment_id for report in reports if report.comment_id is not None}
    counts = {
        comment_id: (total, pending)
        for comment_id, total, pending in db.query(
            CommentReport.comment_id,
            func.count(CommentReport.id),
            func.sum(case((CommentReport.status.in_(["pending", "reviewing"]), 1), else_=0)),
        ).filter(CommentReport.comment_id.in_(ids)).group_by(CommentReport.comment_id).all()
    } if ids else {}
    comments = {comment.id: comment for comment in db.query(Comment).filter(Comment.id.in_(ids)).all()} if ids else {}
    post_ids = {report.post_id for report in reports if report.post_id is not None}
    posts = {post.id: post for post in db.query(Post).filter(Post.id.in_(post_ids)).all()} if post_ids else {}
    for report in reports:
        report.report_count, report.pending_report_count = counts.get(report.comment_id, (0, 0))
        comment = comments.get(report.comment_id)
        if report.comment_id is not None:
            report.post_id = comment.post_id if comment else None
            report.comment_is_hidden = comment.is_hidden if comment else None
        elif report.post_id is not None:
            post = posts.get(report.post_id)
            report.comment_is_hidden = post.is_hidden if post else None
    return reports


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


def create_post_report(
    db: Session,
    user: User,
    post_id: int,
    data: CreatePostReport,
) -> CommentReport:
    post = db.get(Post, post_id)
    if post is None:
        raise LookupError("게시글을 찾을 수 없습니다")
    if post.author_id == user.id:
        raise PermissionError("자신의 게시글은 신고할 수 없습니다")
    if post.is_hidden:
        raise PermissionError("숨김 처리된 게시글은 신고할 수 없습니다")

    existing_report = (
        db.query(CommentReport)
        .filter(
            CommentReport.reporter_id == user.id,
            CommentReport.post_id == post_id,
        )
        .first()
    )
    if existing_report is not None:
        raise ValueError("이미 신고한 게시글입니다")

    report = CommentReport(
        reporter_id=user.id,
        reported_user_id=post.author_id,
        post_id=post.id,
        reason=data.reason.value,
        description=data.description,
        content_snapshot=post.content,
    )
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 신고한 게시글입니다") from exc
    return report


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

    return enrich_reports(db, [report])[0]
