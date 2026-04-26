from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

COLOR_PALETTE = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
    "#BB8FCE", "#85C1E9"
]

class TimetableCourse(Base):
    __tablename__ = "timetable_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timetable_id = Column(Integer, ForeignKey("timetables.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    color = Column(String(20), default="#3B82F6")
    created_at = Column(TIMESTAMP, server_default=func.now())
