from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    blocker_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    blocked_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
    )

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked_user = relationship("User", foreign_keys=[blocked_user_id])

    @property
    def display_name(self) -> str | None:
        return self.blocked_user.name if self.blocked_user is not None else None

    __table_args__ = (
        UniqueConstraint(
            "blocker_id",
            "blocked_user_id",
            name="uq_user_blocks_blocker_blocked",
        ),
        CheckConstraint(
            "blocker_id <> blocked_user_id",
            name="ck_user_blocks_not_self",
        ),
        Index("ix_user_blocks_blocker_id", "blocker_id"),
        Index("ix_user_blocks_blocked_user_id", "blocked_user_id"),
    )
