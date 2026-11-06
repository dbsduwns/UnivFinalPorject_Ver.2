from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type = Column(String(50), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=False, default=dict)
    read_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user = relationship("User", back_populates="notifications")
