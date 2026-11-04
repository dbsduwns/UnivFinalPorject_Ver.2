from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    String,
    TIMESTAMP,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class StudentVerificationSession(Base):
    """ 강남대 학생 인증 """

    __tablename__ = "student_verification_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    onboarding_session_id = Column(
        Integer,
        ForeignKey("oauth_onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_email = Column(String(320), nullable=False)
    otp_hash = Column(String(255), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")

    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    invalidated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_sent_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    onboarding_session = relationship(
        "OauthOnboardingSession",
        back_populates="student_verification_sessions"
    )

    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0",
            name="ch_student_verification_attempt_count_nonnegative",
        ),
        Index(
            "ix_student_verification_onboarding_session_id",
            "onboarding_session_id",
        ),
        Index(
            "ix_student_verification_student_email",
            "student_email",
        ),
        Index(
            "ix_student_verification_expires_at",
            "expires_at",
        )
    )
