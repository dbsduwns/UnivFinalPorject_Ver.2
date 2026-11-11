from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    session_id = Column(String(64), unique=True, nullable=False, index=True)
    current_jti_hash = Column(String(64), nullable=False)

    biometric_enabled = Column(Boolean, nullable=False, default=False)
    biometric_locked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_biometric_at = Column(TIMESTAMP(timezone=True), nullable=True)
    auth_level = Column(String(20), nullable=False, default="standard", server_default="standard")

    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_sessions")
