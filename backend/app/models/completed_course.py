from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class CompletedCourse(Base):
    __tablename__ = "completed_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    semester = Column(String(20), nullable=False)
    grade = Column(String(10))