from sqlalchemy import Column, ForeignKey, Integer, Time
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.database import Base


class ShuttleMapScheduleStop(Base):
    """특정 셔틀 운행의 정류장별 도착시간."""

    __tablename__ = "shuttle_map_schedule_stops"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "stop_id",
            name="uq_shuttle_map_schedule_stop",
        ),
        UniqueConstraint(
            "schedule_id",
            "stop_order",
            name="uq_shuttle_map_schedule_stop_order",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(
        Integer,
        ForeignKey("shuttle_map_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stop_id = Column(
        Integer,
        ForeignKey("shuttle_map_stops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    arrival_time = Column(Time, nullable=False)
    stop_order = Column(Integer, nullable=False)

    schedule = relationship("ShuttleMapSchedule", back_populates="stop_times")
    stop = relationship("ShuttleMapStop", back_populates="schedule_stops")
