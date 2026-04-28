from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("subject_id", "section"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    section = Column(String, nullable=False)
    professor = Column(String)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    max_students = Column(Integer)
    current_students = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    subject = relationship("Subject", back_populates="courses")
    room = relationship("Room", back_populates="courses")
    schedules = relationship("CourseSchedule", back_populates="course")
