from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    session_id = Column(String(64), unique=True, nullable=False, index=True)
    current_jti_hash = Column(String(64), nullable=False)

    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)

    refresh_sessions = relationship(
        "RefreshSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    user = relationship("User", back_populates="refresh_sessions")