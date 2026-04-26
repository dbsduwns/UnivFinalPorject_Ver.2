from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class NoticeRead(Base):
    __tablename__ = "notice_reads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    notice_id = Column(Integer, ForeignKey("notices.id"))
    read_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="notice_reads")
    notice = relationship("Notice", back_populates="notice_reads")