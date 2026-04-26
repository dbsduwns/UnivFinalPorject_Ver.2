from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class WizardSelection(Base):
    __tablename__ = "wizard_selections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    semester = Column(String(20), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    user=relationship("User", back_populates="wizard_selections")
    subject=relationship("Subject", back_populates="wizard_selections")