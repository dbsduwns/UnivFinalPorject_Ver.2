from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    category = Column(String, nullable=False)
    source_url = Column(String)
    attachment_url = Column(String)
    is_important = Column(Boolean, default=False)
    published_at = Column(TIMESTAMP)
    crawled_at = Column(TIMESTAMP, server_default=func.now())

    notice_reads = relationship("NoticeRead", back_populates="notice")