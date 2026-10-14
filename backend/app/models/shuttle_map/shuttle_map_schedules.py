from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Time, text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.database import Base


class ShuttleMapSchedule(Base):
    """요일별 캠퍼스 셔틀 운행 일정."""

    __tablename__ = "shuttle_map_schedules"
    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "day_of_week",
            "departure_time",
            name="uq_shuttle_map_schedule_departure",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(
        Integer,
        ForeignKey("shuttle_map_routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week = Column(String(3), nullable=False, index=True)
    departure_time = Column(Time, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    route = relationship("ShuttleMapRoute", back_populates="schedules")
    stop_times = relationship(
        "ShuttleMapScheduleStop",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="ShuttleMapScheduleStop.stop_order",
    )
