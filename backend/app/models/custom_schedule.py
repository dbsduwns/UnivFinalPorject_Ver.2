from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class CustomSchedule(Base):
    __tablename__ = "custom_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timetable_id = Column(Integer, ForeignKey("timetable.id"), nullable=False)
    name = Column(String(100), nullable=False)
    day_of_week = Column(String(10), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    color = Column(str(20), default="#3B82F6")
    memo = Column(String(200))

    timetable = relationship("Timetable", back_populates="custom_schedules")