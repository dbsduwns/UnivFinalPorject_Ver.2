from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class RoomParticipant(Base):
    __tablename__ = "room_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("room_messengers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    last_read = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="room_participants")
    room = relationship("RoomMessenger", back_populates="participants")

    __table_args__ = (
        UniqueConstraint(
            "room_id", 
            "user_id", 
            name="uq_room_participant",
        ),
    )
