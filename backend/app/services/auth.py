from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserLogin, UserSignup


def signup(db: Session, data: UserSignup):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise ValueError("이미 존재하는 이메일입니다")
    existing_student = db.query(User).filter(User.student_id == data.student_id).first()
    if existing_student:
        raise ValueError("이미 존재하는 학번입니다")

    hashed = hash_password(data.password)

    user = User(
        email=data.email,
        password_hash=hashed,
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

    token_data = {"sub": str(user.id), "token_version": user.token_version}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }
