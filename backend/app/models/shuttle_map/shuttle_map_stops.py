from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class ShuttleMapStop(Base):
    """캠퍼스 셔틀 정류장."""

    __tablename__ = "shuttle_map_stops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stop_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    schedule_stops = relationship(
        "ShuttleMapScheduleStop",
        back_populates="stop",
        cascade="all, delete-orphan",
    )
