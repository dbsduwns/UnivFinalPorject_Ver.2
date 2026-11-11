from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship

from app.database import Base


class BiometricCredential(Base):
    __tablename__ = "biometric_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_session_id = Column(
        String(64),
        ForeignKey("refresh_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    credential_hash = Column(String(64), nullable=False, unique=True, index=True)
    device_id_hash = Column(String(64), nullable=False, index=True)
    platform = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="biometric_credentials")
