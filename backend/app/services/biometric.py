import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_biometric_credential
from app.models.biometric_Credential import BiometricCredential
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.services.auth import issue_token_pair


def _hash_device_id(device_id: str) -> str:
    return hashlib.sha256(device_id.encode("utf-8")).hexdigest()


def register_credential(
    db: Session,
    user: User,
    credential: str,
    device_id: str,
    platform: str,
    refresh_session: RefreshSession | None,
) -> BiometricCredential:
    credential_hash = hash_biometric_credential(credential)
    device_id_hash = _hash_device_id(device_id)

    row = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.user_id == user.id,
            BiometricCredential.device_id_hash == device_id_hash,
            BiometricCredential.revoked_at.is_(None),
        )
        .first()
    )
    if row is None:
        row = BiometricCredential(
            user_id=user.id,
            credential_hash=credential_hash,
            device_id_hash=device_id_hash,
            platform=platform,
        )
        db.add(row)
    else:
        row.credential_hash = credential_hash
        row.platform = platform
        row.revoked_at = None

    if refresh_session is not None:
        refresh_session.biometric_enabled = True
        refresh_session.biometric_locked_at = None
        row.refresh_session_id = refresh_session.session_id

    db.commit()
    db.refresh(row)
    return row


def unlock(
    db: Session,
    credential: str,
    device_id: str,
) -> dict:
    credential_hash = hash_biometric_credential(credential)
    device_id_hash = _hash_device_id(device_id)
    row = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.credential_hash == credential_hash,
            BiometricCredential.device_id_hash == device_id_hash,
            BiometricCredential.revoked_at.is_(None),
        )
        .first()
    )
    if row is None or row.user is None or not row.user.is_active:
        raise ValueError("생체 인증 정보가 유효하지 않습니다.")

    now = datetime.now(timezone.utc)
    if row.refresh_session_id:
        old_session = (
            db.query(RefreshSession)
            .filter(RefreshSession.session_id == row.refresh_session_id)
            .first()
        )
        if old_session is not None and old_session.revoked_at is None:
            old_session.revoked_at = now

    tokens = issue_token_pair(db, row.user, auth_level="biometric")
    row.last_used_at = now
    row.refresh_session_id = tokens["session_id"]
    new_session = (
        db.query(RefreshSession)
        .filter(RefreshSession.session_id == tokens["session_id"])
        .first()
    )
    if new_session is not None:
        new_session.biometric_enabled = True
        new_session.last_biometric_at = now
        new_session.biometric_locked_at = None
    db.commit()

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }


def lock_session(db: Session, user: User, session_id: str) -> None:
    session = (
        db.query(RefreshSession)
        .filter(
            RefreshSession.session_id == session_id,
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is None:
        raise ValueError("세션을 찾을 수 없습니다.")
    if session.biometric_enabled:
        session.biometric_locked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_credentials(db: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    db.query(BiometricCredential).filter(
        BiometricCredential.user_id == user.id,
        BiometricCredential.revoked_at.is_(None),
    ).update({BiometricCredential.revoked_at: now}, synchronize_session=False)
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user.id,
        RefreshSession.biometric_enabled.is_(True),
        RefreshSession.revoked_at.is_(None),
    ).update({RefreshSession.revoked_at: now}, synchronize_session=False)
    db.commit()
