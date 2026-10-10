from sqlalchemy.orm import Session

from app.models.user import User


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
