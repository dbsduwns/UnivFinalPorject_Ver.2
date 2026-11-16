from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_token
from app.models.refresh_session import RefreshSession
from app.models.user import User

bearer_scheme = HTTPBearer()


@dataclass
class AuthContext:
    user: User
    payload: dict
    refresh_session: RefreshSession | None


def has_recent_biometric_auth(context: AuthContext, max_age_seconds: int = 300) -> bool:
    """최근 OS 생체 인증으로 발급된 세션인지 확인한다."""
    if context.payload.get("auth_level") != "biometric":
        return False
    last_biometric_at = context.refresh_session.last_biometric_at if context.refresh_session else None
    if last_biometric_at is None:
        return False
    if last_biometric_at.tzinfo is None:
        last_biometric_at = last_biometric_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_biometric_at <= timedelta(seconds=max_age_seconds)


def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")
    if payload.get("token_version") != user.token_version:
        raise HTTPException(status_code=401, detail="Session has expired")

    refresh_session = None
    session_id = payload.get("session_id")
    if session_id:
        refresh_session = (
            db.query(RefreshSession)
            .filter(
                RefreshSession.session_id == session_id,
                RefreshSession.user_id == user.id,
            )
            .first()
        )
        if refresh_session is None or refresh_session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Session has expired")

        if refresh_session.biometric_locked_at is not None:
            issued_at = payload.get("iat")
            if issued_at is None:
                raise HTTPException(status_code=401, detail="Biometric authentication required")
            if isinstance(issued_at, (int, float)):
                issued_at = datetime.fromtimestamp(issued_at, tz=timezone.utc)
            if issued_at <= refresh_session.biometric_locked_at:
                raise HTTPException(status_code=401, detail="Biometric authentication required")

    return AuthContext(user=user, payload=payload, refresh_session=refresh_session)


def get_current_user(
    context: AuthContext = Depends(get_current_auth_context),
):
    return context.user

def get_current_admin_user(
        current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permision required")
    return current_user
