from sqlalchemy import Boolean, Column, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserPresence(Base):
    """사용자가 현재 앱에서 보고 있는 대화방 상태입니다.

    사용자당 한 행만 유지합니다. ``last_seen_at``은 클라이언트의 heartbeat로
    갱신하며, 오래된 행은 오프라인 상태로 취급합니다.
    """

    __tablename__ = "user_presences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    active_room_id = Column(
        Integer,
        ForeignKey("room_messengers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_app_foreground = Column(Boolean, nullable=False, default=False, server_default="false")
    last_seen_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    user = relationship("User", back_populates="presence")
    active_room = relationship("RoomMessenger", back_populates="active_presences")
