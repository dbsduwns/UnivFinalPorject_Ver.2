import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.models.oauth_onboarding_sessions import OauthOnboardingSession
from app.models.user import User
from app.models.user_identitiy import UserIdentity
from app.services.auth import issue_token_pair


OAUTH_ONBOARDING_EXPIRE_MINUTES = 10


def hash_onboarding_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_google_id_token(raw_id_token: str) -> dict:
    if not raw_id_token:
        raise HTTPException(
            status_code=400,
            detail="Google ID token이 필요합니다.",
        )

    configured_ids = os.getenv("GOOGLE_CLIENT_IDS") or os.getenv(
        "GOOGLE_CLIENT_ID",
        "",
    )
    allowed_client_ids = {
        value.strip()
        for value in configured_ids.split(",")
        if value.strip()
    }
    if not allowed_client_ids:
        raise RuntimeError(
            "GOOGLE_CLIENT_IDS 또는 GOOGLE_CLIENT_ID가 설정되지 않았습니다."
        )

    try:
        info = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            audience=None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 Google ID token입니다.",
        ) from exc

    if info.get("aud") not in allowed_client_ids:
        raise HTTPException(
            status_code=401,
            detail="Google token audience가 허용되지 않았습니다.",
        )

    if info.get("iss") not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise HTTPException(
            status_code=401,
            detail="Google token 발급자가 유효하지 않습니다.",
        )

    if not info.get("email_verified"):
        raise HTTPException(
            status_code=401,
            detail="Google 이메일 인증이 완료되지 않았습니다.",
        )

    if not info.get("sub") or not info.get("email"):
        raise HTTPException(
            status_code=401,
            detail="Google 사용자 식별자 또는 이메일이 없습니다.",
        )

    return info


def create_oauth_onboarding_session(
    db: Session,
    provider_subject: str,
    provider_email: str,
    name: str,
) -> tuple[OauthOnboardingSession, str]:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    session = OauthOnboardingSession(
        provider="google",
        provider_subject=provider_subject,
        provider_email=provider_email.strip().lower(),
        name=name.strip() or "Google User",
        onboarding_token_hash=hash_onboarding_token(raw_token),
        expires_at=now + timedelta(minutes=OAUTH_ONBOARDING_EXPIRE_MINUTES),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def authenticate_google_user(db: Session, raw_id_token: str) -> dict:
    """Authenticate Google identity without completing student verification."""
    info = verify_google_id_token(raw_id_token)
    provider_subject = info["sub"]
    provider_email = info["email"].strip().lower()
    name = info.get("name") or "Google User"

    identity = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.provider == "google",
            UserIdentity.provider_subject == provider_subject,
        )
        .first()
    )
    if identity:
        user = identity.user
        if not user.is_active:
            raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

        tokens = issue_token_pair(db, user)
        return {
            "status": "authenticated",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    existing_user = (
        db.query(User)
        .filter(User.email == provider_email)
        .first()
    )
    if existing_user:
        return {
            "status": "link_required",
            "email": provider_email,
            "message": (
                "기존 계정으로 로그인한 뒤 Google 계정 연결을 진행해야 합니다."
            ),
        }

    onboarding_session, onboarding_token = create_oauth_onboarding_session(
        db=db,
        provider_subject=provider_subject,
        provider_email=provider_email,
        name=name,
    )
    return {
        "status": "student_verification_required",
        "onboarding_token": onboarding_token,
        "expires_at": onboarding_session.expires_at,
    }
