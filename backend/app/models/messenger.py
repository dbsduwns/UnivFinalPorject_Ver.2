from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Messenger(Base):
    __tablename__ = "messengers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_messenger_id = Column(Integer, ForeignKey("room_messengers.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    sender = relationship("User", back_populates="messengers")
    room = relationship("RoomMessenger", back_populates="messages")
