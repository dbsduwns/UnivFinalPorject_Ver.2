from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.notice import Notice
from app.models.community.post import Post
from app.models.community.comment_report import CommentReport
from app.services import account as account_service


def update_admin_role(
    db: Session,
    current_admin: User,
    target_user_id: int,
    is_admin: bool,
) -> User:
    target_user = db.get(User, target_user_id)
    if target_user is None:
        raise LookupError("사용자를 찾을 수 없습니다")

    if not target_user.is_active:
        raise ValueError("비활성 사용자에게는 관리자 권한을 부여할 수 없습니다")

    if target_user.id == current_admin.id and not is_admin:
        raise ValueError("자신의 관리자 권한은 직접 해제할 수 없습니다")

    if target_user.is_admin == is_admin:
        return target_user

    if not is_admin:
        admin_count = (
            db.query(User)
            .filter(User.is_admin.is_(True), User.is_active.is_(True))
            .count()
        )
        if admin_count <= 1:
            raise ValueError("마지막 관리자의 권한은 해제할 수 없습니다")

    target_user.is_admin = is_admin

    try:
        db.commit()
        db.refresh(target_user)
    except Exception:
        db.rollback()
        raise

    return target_user


def update_user_active_status(db: Session, current_admin: User, target_user_id: int, is_active: bool) -> User:
    target_user = db.get(User, target_user_id)
    if target_user is None:
        raise LookupError("사용자를 찾을 수 없습니다")
    if target_user.id == current_admin.id and not is_active:
        raise ValueError("자신의 계정은 직접 비활성화할 수 없습니다")
    if target_user.is_admin and not is_active:
        if db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).count() <= 1:
            raise ValueError("마지막 활성 관리자는 비활성화할 수 없습니다")
    target_user.is_active = is_active
    if not is_active:
        target_user.token_version += 1
    try:
        db.commit()
        db.refresh(target_user)
    except Exception:
        db.rollback()
        raise
    return target_user


def get_dashboard(db: Session) -> dict:
    reports = db.query(CommentReport).order_by(CommentReport.created_at.desc(), CommentReport.id.desc()).limit(5).all()
    return {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "active_users": db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0,
        "admin_users": db.query(func.count(User.id)).filter(User.is_admin.is_(True)).scalar() or 0,
        "total_posts": db.query(func.count(Post.id)).scalar() or 0,
        "hidden_posts": db.query(func.count(Post.id)).filter(Post.is_hidden.is_(True)).scalar() or 0,
        "pending_reports": db.query(func.count(CommentReport.id)).filter(CommentReport.status.in_(("pending", "reviewing"))).scalar() or 0,
        "notices": db.query(func.count(Notice.id)).scalar() or 0,
        "recent_reports": [{"id": r.id, "reason": r.reason, "status": r.status, "content_snapshot": r.content_snapshot, "created_at": r.created_at} for r in reports],
    }


def delete_user_account(db: Session, current_admin: User, target_user_id: int) -> None:
    """관리자가 다른 회원의 계정과 연결된 데이터를 영구 삭제한다."""
    target_user = db.get(User, target_user_id)
    if target_user is None:
        raise LookupError("사용자를 찾을 수 없습니다")
    if target_user.id == current_admin.id:
        raise ValueError("자신의 계정은 관리자 화면에서 삭제할 수 없습니다")
    if target_user.is_admin:
        active_admins = db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).count()
        if target_user.is_active and active_admins <= 1:
            raise ValueError("마지막 활성 관리자는 삭제할 수 없습니다")
    try:
        account_service.delete_account(db, target_user)
    except Exception:
        db.rollback()
        raise
