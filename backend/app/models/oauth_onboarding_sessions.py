from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    String,
    TIMESTAMP,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class OauthOnboardingSession(Base):
    """ 구글 로그인 인증 """

    __tablename__ = "oauth_onboarding_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(20), nullable=False)
    provider_subject = Column(String(255), nullable=False)
    provider_email = Column(String(320), nullable=False)
    name = Column(String(100), nullable=False)
    onboarding_token_hash = Column(String(255), nullable=False, unique=True)

    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    consumed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    student_verification_sessions = relationship(
        "StudentVerificationSession",
        back_populates="onboarding_session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "provider IN ('google')",
            name="ck_oauth_onboarding_sessions_provider",
        ),
        Index(
            "ix_oauth_onboarding_sessions_provider_subject",
            "provider",
            "provider_subject",
        ),
        Index(
            "ix_oauth_onboarding_sessions_expires_at",
            "expires_at",
        ),
    )
