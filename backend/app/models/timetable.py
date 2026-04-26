from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    semester = Column(String, nullable=False)
    is_main = Column(Boolean, default=False)
    share_token = Column(String(100), unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="timetables")
    custom_schedules = relationship("CustomSchedule", back_populates='timetable')