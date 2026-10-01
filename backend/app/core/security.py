from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os


SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 14
FRIEND_INVITE_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

def hash_password(password: str) -> str:
    """비밀번호를 해싱해서 반환"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ 입력한 비밀번호와 해싱된 비밀번호를 비교 """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """ 엑세스 토큰 생성 """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """ 리프레시 토큰 생성 """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    """ 토큰을 해석해서 데이터로 변환 """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def create_friend_invite_token(inviter_id: int) -> tuple[str, datetime]:
    """친구 초대 링크에 사용할 7일 만료 서명 토큰을 생성합니다."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=FRIEND_INVITE_EXPIRE_DAYS)
    token = jwt.encode(
        {
            "sub": str(inviter_id),
            "purpose": "friend_invite",
            "exp": expires_at,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token, expires_at


def decode_friend_invite_token(token: str) -> int | None:
    """유효한 친구 초대 토큰이면 초대한 사용자 ID를 반환합니다."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "friend_invite":
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        return None
