from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserSignup, UserLogin
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token

def signup(db: Session, data: UserSignup):

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise ValueError("이미 존재하는 이메일입니다")

    hashed = hash_password(data.password)

    user = User(
        email=data.email,
        password_hash=hashed,
        name=data.name
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
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }