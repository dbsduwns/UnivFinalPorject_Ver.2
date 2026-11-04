import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    hash_jti,
    hash_password,
    verify_password,
)
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.user import UserLogin, UserSignup


def signup(db: Session, data: UserSignup):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise ValueError("이미 존재하는 이메일입니다")

    existing_student = (
        db.query(User)
        .filter(User.student_id == data.student_id)
        .first()
    )
    if existing_student:
        raise ValueError("이미 존재하는 학번입니다")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        student_id=data.student_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, data: UserLogin):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise ValueError("해당 이메일의 계정을 찾을 수 없습니다")
    if not verify_password(data.password, user.password_hash):
        raise ValueError("비밀번호가 일치하지 않습니다")
    if not user.is_active:
        raise ValueError("비활성화된 계정입니다")

    return issue_token_pair(db, user)


def issue_token_pair(db: Session, user: User) -> dict:
    """Create a refresh session and access/refresh token pair."""
    session_id = secrets.token_urlsafe(32)
    jti = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS,
    )

    db.add(
        RefreshSession(
            user_id=user.id,
            session_id=session_id,
            current_jti_hash=hash_jti(jti),
            expires_at=expires_at,
        )
    )
    db.flush()

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "token_version": user.token_version,
        }
    )
    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
            "token_version": user.token_version,
            "session_id": session_id,
            "jti": jti,
        }
    )
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


def verify_user_password(db: Session, user_id: int, password: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    return user is not None and verify_password(password, user.password_hash)


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("현재 비밀번호가 일치하지 않습니다.")
    if new_password != confirm_password:
        raise ValueError("새 비밀번호와 비밀번호 재입력이 일치하지 않습니다.")
    if current_password == new_password:
        raise ValueError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    db.commit()
