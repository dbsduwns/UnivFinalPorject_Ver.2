from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class RoomMessenger(Base):
    __tablename__ = "room_messengers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_group = Column(Boolean, nullable=False, default=False, server_default="false")
    name = Column(String(100), nullable=True)
    # 정렬한 두 사용자 ID입니다. 단체방은 NULL로 두어 같은 멤버의 방도 생성할 수 있습니다.
    direct_key = Column(String(64), unique=True, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    participants = relationship("RoomParticipant", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Messenger", back_populates="room", cascade="all, delete-orphan")
