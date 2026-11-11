import hashlib
import hmac
import os
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 14
FRIEND_INVITE_EXPIRE_DAYS = 7
RESET_TOKEN_EXPIRE_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def load_secret_key() -> str:
    value = os.getenv("SECRET_KEY")

    if not value:
        raise RuntimeError("SECRET_KEY 환경 변수가 설정되지 않았습니다.")

    value = value.strip()

    invalid_values = {
        "fallback-secret-key",
        "replace_with_a_long_random_secret",
        "changeme",
        "your-secret-key",
    }

    if value in invalid_values:
        raise RuntimeError("SECRET_KEY에 예시용 기본값을 사용할 수 없습니다.")

    # token_urlsafe(32) 기준 약 43자 이상
    if len(value) < 43:
        raise RuntimeError("SECRET_KEY는 최소 32바이트 이상의 무작위값이어야 합니다.")

    return value

SECRET_KEY = load_secret_key()

def hash_password(password: str) -> str:
    """비밀번호를 해싱해서 반환"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ 입력한 비밀번호와 해싱된 비밀번호를 비교 """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """ 엑세스 토큰 생성 """
    to_encode = data.copy()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"type": "access", "iat": datetime.now(timezone.utc), "exp": expires_at})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """ 리프레시 토큰 생성 """
    to_encode = data.copy()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"type": "refresh", "exp": expires_at})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    """ 토큰을 해석해서 데이터로 변환 """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def hash_jti(jti: str) -> str:
    """ JTI를 해싱 """
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def hash_biometric_credential(credential: str) -> str:
    """Hash a high-entropy device credential without storing the raw value."""
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        credential.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

def create_reset_token() -> str:
    """ 비밀번호 재설정 토큰 생성 (무작위 난수 32) """
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    """ 비밀번호 재설정 토큰 해싱 """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
