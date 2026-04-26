from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class GraduationStandard(Base):
    __tablename__ = "graduation_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(20), nullable=False)
    credit_major = Column(Integer, nullable=False)
    credit_culture = Column(Integer, nullable=False)
    total_credit = Column(Integer, nullable=False)
    graduation_eval = Column(Boolean, nullable=False, default=False)