from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    room_number = Column(String, nullable=False)
    floor = Column(Integer)
    capacity = Column(Integer)
    room_type = Column(String)

    building = relationship("Building", back_populates="rooms")