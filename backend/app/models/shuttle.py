from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class Shuttle(Base):
    __tablename__ = "shuttle"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    is_active = Column(Integer, server_default="1") # 1: 활성, 0: 비활성
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
