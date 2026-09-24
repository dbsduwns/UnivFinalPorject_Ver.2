from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requester_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    addressee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, ACCEPTED, REJECTED
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    requester = relationship("User", foreign_keys=[requester_id], backref="sent_friendships")
    addressee = relationship("User", foreign_keys=[addressee_id], backref="received_friendships")

    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_requester_addressee"),
    )
