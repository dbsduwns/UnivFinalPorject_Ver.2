from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.database import Base


class SubwayLineStation(Base):
    """지하철 노선별 역 순서의 정적 캐시.

    실시간 열차 위치 조회 전마다 서울 열린데이터광장에 연결하지 않도록
    노선·역·순서만 별도로 보관한다.
    """

    __tablename__ = "subway_line_stations"
    __table_args__ = (
        UniqueConstraint("line_name", "station_code", "stop_order", name="uq_subway_line_station_order"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_name = Column(String(50), nullable=False, index=True)
    station_code = Column(String(50), nullable=False)
    station_name = Column(String(120), nullable=False)
    stop_order = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
