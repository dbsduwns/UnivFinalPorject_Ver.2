from sqlalchemy import Column, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("subject_code", "semester", name="uq_subjects_subject_code_semester"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    subject_code = Column(String, nullable=False)
    department = Column(String)
    credits = Column(Integer, nullable=False)
    course_type = Column(String)
    semester = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    courses = relationship("Course", back_populates="subject")
    wizard_selections = relationship("WizardSelection", back_populates="subject")
