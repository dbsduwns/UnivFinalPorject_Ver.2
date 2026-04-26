from sqlalchemy import Column, Integer, String, Float, Text
from app.database import Base

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    short_name = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    floors = Column(Integer)
    description = Column(Text)
    image_url = Column(String)