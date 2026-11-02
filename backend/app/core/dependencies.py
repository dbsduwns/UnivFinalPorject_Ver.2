from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    # 토큰 존재 여부 확인
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    # 사용자 ID 확인
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    # 사용자 확인(비활성화 여부도)
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")
    # 토큰 타입 확인
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    # 토큰 버전 확인
    token_version = payload.get("token_version")
    if token_version is None or token_version != user.token_version:
        raise HTTPException(status_code=401, detail="Session has expired")

    return user

def get_current_admin_user(
        current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permision required")
    return current_user
