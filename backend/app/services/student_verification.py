import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.email import send_student_verification_email
from app.core.security import hash_password, verify_password
from app.models.oauth_onboarding_sessions import OauthOnboardingSession
from app.models.student_verification_session import StudentVerificationSession
from app.models.user import User
from app.models.user_identitiy import UserIdentity
from app.services.auth import issue_token_pair
from app.services.google_auth import hash_onboarding_token


OTP_EXPIRE_MINUTES = 10
RESEND_INTERVAL_SECONDS = 60


class StudentVerificationRateLimitError(ValueError):
    pass


def _validate_student_email(student_email: str) -> str:
    normalized_email = student_email.strip().lower()
    domain = os.getenv("STUDENT_EMAIL_DOMAIN", "kangnam.ac.kr").strip().lower()
    if not normalized_email.endswith(f"@{domain}"):
        raise ValueError(f"강남대학교 이메일(@{domain})만 사용할 수 있습니다.")
    return normalized_email


def request_account_student_verification(db: Session, user: User, student_email: str) -> dict:
    now = datetime.now(timezone.utc)
    normalized_email = _validate_student_email(student_email)
    if user.student_verified_at is not None:
        raise ValueError("이미 학생 인증이 완료된 계정입니다.")
    existing_student = (
        db.query(User)
        .filter(
            or_(User.student_email == normalized_email, User.email == normalized_email),
            User.id != user.id,
        )
        .first()
    )
    if existing_student is not None:
        raise ValueError("이미 다른 계정에서 인증된 학생 이메일입니다.")

    active_sessions = (
        db.query(StudentVerificationSession)
        .filter(
            StudentVerificationSession.user_id == user.id,
            StudentVerificationSession.verified_at.is_(None),
            StudentVerificationSession.invalidated_at.is_(None),
            StudentVerificationSession.expires_at > now,
        )
        .with_for_update()
        .all()
    )
    if active_sessions:
        latest = max(active_sessions, key=lambda item: item.last_sent_at)
        last_sent_at = latest.last_sent_at
        if last_sent_at.tzinfo is None:
            last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
        elapsed = (now - last_sent_at).total_seconds()
        if elapsed < RESEND_INTERVAL_SECONDS:
            raise StudentVerificationRateLimitError(
                f"{int(RESEND_INTERVAL_SECONDS - elapsed)}초 후에 다시 인증 코드를 요청할 수 있습니다."
            )
        for active in active_sessions:
            active.invalidated_at = now

    otp = f"{secrets.randbelow(1_000_000):06d}"
    session = StudentVerificationSession(
        user_id=user.id,
        student_email=normalized_email,
        otp_hash=hash_password(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
        attempt_count=0,
        last_sent_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    try:
        send_student_verification_email(normalized_email, otp)
    except Exception:
        session.invalidated_at = datetime.now(timezone.utc)
        db.commit()
        raise
    return {
        "verification_id": session.id,
        "student_email": normalized_email,
        "expires_at": session.expires_at,
    }


def confirm_account_student_verification(
    db: Session, user: User, verification_id: int, input_otp: str
) -> None:
    now = datetime.now(timezone.utc)
    session = (
        db.query(StudentVerificationSession)
        .filter(
            StudentVerificationSession.id == verification_id,
            StudentVerificationSession.user_id == user.id,
        )
        .with_for_update()
        .first()
    )
    if session is None:
        raise ValueError("인증 세션을 찾을 수 없습니다.")
    if session.verified_at is not None or session.invalidated_at is not None:
        raise ValueError("더 이상 사용할 수 없는 인증 세션입니다.")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise ValueError("인증 코드가 만료되었습니다.")
    if session.attempt_count >= 5:
        raise ValueError("인증 시도 횟수를 초과했습니다.")
    if not verify_password(input_otp, session.otp_hash):
        session.attempt_count += 1
        db.commit()
        raise ValueError("인증 코드가 올바르지 않습니다.")

    session.verified_at = now
    user.student_verified_at = now
    user.student_email = session.student_email
    db.commit()

def request_student_verification(
    db: Session,
    onboarding_token: str,
    student_email: str,
) -> dict:
    now = datetime.now(timezone.utc)
    normalized_email = student_email.strip().lower()
    domain = os.getenv("STUDENT_EMAIL_DOMAIN", "kangnam.ac.kr").strip().lower()

    if not normalized_email.endswith(f"@{domain}"):
        raise ValueError(
            f"강남대학교 이메일(@{domain})만 사용할 수 있습니다."
        )

    onboarding = (
        db.query(OauthOnboardingSession)
        .filter(
            OauthOnboardingSession.onboarding_token_hash
            == hash_onboarding_token(onboarding_token),
        )
        .with_for_update()
        .first()
    )
    if onboarding is None:
        raise ValueError("유효하지 않은 가입 세션입니다.")
    if onboarding.consumed_at is not None:
        raise ValueError("이미 완료된 가입 세션입니다.")
    if onboarding.expires_at <= now:
        raise ValueError("가입 세션이 만료되었습니다.")

    active_sessions = (
        db.query(StudentVerificationSession)
        .filter(
            StudentVerificationSession.onboarding_session_id == onboarding.id,
            StudentVerificationSession.verified_at.is_(None),
            StudentVerificationSession.invalidated_at.is_(None),
            StudentVerificationSession.expires_at > now,
        )
        .with_for_update()
        .all()
    )
    if active_sessions:
        latest = max(active_sessions, key=lambda item: item.last_sent_at)
        latest_sent_at = latest.last_sent_at
        if latest_sent_at.tzinfo is None:
            latest_sent_at = latest_sent_at.replace(tzinfo=timezone.utc)
        elapsed = (now - latest_sent_at).total_seconds()
        if elapsed < RESEND_INTERVAL_SECONDS:
            remaining = int(RESEND_INTERVAL_SECONDS - elapsed)
            raise StudentVerificationRateLimitError(
                f"{remaining}초 후에 다시 인증 코드를 요청할 수 있습니다."
            )

        for active in active_sessions:
            active.invalidated_at = now

    otp = f"{secrets.randbelow(1_000_000):06d}"
    session = StudentVerificationSession(
        onboarding_session_id=onboarding.id,
        student_email=normalized_email,
        otp_hash=hash_password(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
        attempt_count=0,
        last_sent_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        send_student_verification_email(normalized_email, otp)
    except Exception:
        session.invalidated_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return {
        "verification_id": session.id,
        "student_email": normalized_email,
        "expires_at": session.expires_at,
    }


def confirm_student_verification(
    db: Session,
    verification_id: int,
    onboarding_token: str,
    input_otp: str,
) -> dict:
    now = datetime.now(timezone.utc)
    session = (
        db.query(StudentVerificationSession)
        .filter(StudentVerificationSession.id == verification_id)
        .with_for_update()
        .first()
    )

    if session is None:
        raise ValueError("인증 세션을 찾을 수 없습니다.")
    if session.verified_at is not None:
        raise ValueError("이미 인증이 완료된 세션입니다.")
    if session.invalidated_at is not None:
        raise ValueError("더 이상 사용할 수 없는 인증 세션입니다.")

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise ValueError("인증 코드가 만료되었습니다.")
    if session.attempt_count >= 5:
        raise ValueError("인증 시도 횟수를 초과했습니다.")

    onboarding = session.onboarding_session

    if onboarding is None:
        raise ValueError("가입 세션을 찾을 수 없습니다.")
    if onboarding.consumed_at is not None:
        raise ValueError("이미 완료된 가입 세션입니다.")

    onboarding_expires_at = onboarding.expires_at
    if onboarding_expires_at.tzinfo is None:
        onboarding_expires_at = onboarding_expires_at.replace(tzinfo=timezone.utc)

    if onboarding_expires_at <= now:
        raise ValueError("가입 세션이 만료되었습니다.")
    if hash_onboarding_token(onboarding_token) != onboarding.onboarding_token_hash:
        raise ValueError("유효하지 않은 가입토큰입니다.")
    if not verify_password(input_otp, session.otp_hash):
        session.attempt_count += 1
        db.commit()
        raise ValueError("인증 코드가 올바르지 않습니다.")

    existing_user = (
        db.query(User)
        .filter(
            or_(
                User.student_email == session.student_email,
                User.email == session.student_email,
            )
        )
        .first()
    )
    if existing_user is not None:
        raise ValueError("이미 가입된 학생 이메일입니다.")

    user = User(
        email=session.student_email,
        student_email=session.student_email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        name=onboarding.name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        UserIdentity(
            user_id=user.id,
            provider=onboarding.provider,
            provider_subject=onboarding.provider_subject,
            provider_email=onboarding.provider_email,
        )
    )
    session.verified_at = now
    onboarding.consumed_at = now

    tokens = issue_token_pair(db, user)
    return {
        "status": "authenticated",
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }
