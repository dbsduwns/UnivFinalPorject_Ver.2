from datetime import datetime, timedelta, timezone
import hashlib
import logging
from sqlalchemy.orm import Session

from app.core.security import (
    RESET_TOKEN_EXPIRE_MINUTES,
    hash_password,
    create_reset_token,
    hash_reset_token,
)
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.models.password_reset_request_log import PasswordResetRequestLog
from app.core.email import send_password_reset_email

logger = logging.getLogger(__name__)

RESET_REQUEST_EMAIL_LIMIT = 3
RESET_REQUEST_EMAIL_WINDOW = timedelta(minutes=15)
RESET_REQUEST_IP_LIMIT = 10
RESET_REQUEST_IP_WINDOW = timedelta(hours=1)


class PasswordResetRateLimitExceeded(ValueError):
    pass


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def _record_reset_request_or_raise(db: Session, email: str, client_ip: str, now: datetime) -> None:
    email_hash = _hash_email(email)
    email_requests = db.query(PasswordResetRequestLog).filter(
        PasswordResetRequestLog.email_hash == email_hash,
        PasswordResetRequestLog.created_at >= now - RESET_REQUEST_EMAIL_WINDOW,
    ).count()
    ip_requests = db.query(PasswordResetRequestLog).filter(
        PasswordResetRequestLog.ip_address == client_ip,
        PasswordResetRequestLog.created_at >= now - RESET_REQUEST_IP_WINDOW,
    ).count()

    if email_requests >= RESET_REQUEST_EMAIL_LIMIT or ip_requests >= RESET_REQUEST_IP_LIMIT:
        raise PasswordResetRateLimitExceeded("비밀번호 재설정 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")

    db.add(PasswordResetRequestLog(email_hash=email_hash, ip_address=client_ip, created_at=now))

def request_password_reset(db: Session, email: str, client_ip: str) -> None:
    now = datetime.now(timezone.utc)
    _record_reset_request_or_raise(db, email, client_ip, now)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        db.commit()
        return

    # A new request invalidates every previous reset link for this user.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
    ).delete(synchronize_session=False)

    raw_token = create_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(reset_token)
    db.commit()

    try:
        send_password_reset_email(user.email, raw_token)
    except RuntimeError:
        db.delete(reset_token)
        db.commit()
        logger.exception("Password reset email delivery failed")


def confirm_password_reset(
        db: Session,
        token: str,
        new_password: str,
        confirm_password: str
    ) -> None:

    if new_password != confirm_password:
        raise ValueError("확인 비밀번호가 일치하지 않습니다")

    received_hash = hash_reset_token(token)

    now = datetime.now(timezone.utc)
    reset_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == received_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).first()

    if reset_record is None:
        raise ValueError("링크가 만료되었거나 유효하지 않습니다.")

    user = db.get(User, reset_record.user_id)
    if user is None:
        raise ValueError("링크가 만료되었거나 유효하지 않습니다.")
    user.password_hash = hash_password(new_password)
    user.token_version += 1

    reset_record.used_at = now

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != reset_record.id,
    ).delete(synchronize_session=False)

    db.commit()

