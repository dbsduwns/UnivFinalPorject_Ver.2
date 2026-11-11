from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False, unique=True)
    student_email = Column(String(320), nullable=True, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    student_id = Column(String, unique=True)
    department = Column(String)
    grade = Column(Integer)
    avatar_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    is_admin = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, server_default="0", nullable=False)
    student_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)

    timetables = relationship("Timetable", back_populates="user")
    chat_rooms = relationship("ChatRoom", back_populates="user")
    notice_reads = relationship("NoticeRead", back_populates="user")
    notification_setting = relationship("NotificationSetting", back_populates="user", uselist=False)
    notifications = relationship(
        "UserNotification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    presence = relationship(
        "UserPresence",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    wizard_selections = relationship("WizardSelection", back_populates="user")
    messengers = relationship("Messenger", back_populates="sender")
    room_participants = relationship("RoomParticipant", back_populates="user", cascade="all, delete-orphan")
    commute_profile = relationship(
        "CommuteProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    refresh_sessions = relationship(
        "RefreshSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    biometric_credentials = relationship(
        "BiometricCredential",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    identities = relationship(
        "UserIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    student_verification_sessions = relationship(
        "StudentVerificationSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
