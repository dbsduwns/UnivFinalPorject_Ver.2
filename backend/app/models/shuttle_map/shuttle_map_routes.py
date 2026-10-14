from sqlalchemy import Boolean, Column, Integer, String, text
from sqlalchemy.orm import relationship

from app.database import Base


class ShuttleMapRoute(Base):
    """캠퍼스 셔틀 노선."""

    __tablename__ = "shuttle_map_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    schedules = relationship(
        "ShuttleMapSchedule",
        back_populates="route",
        cascade="all, delete-orphan",
    )
