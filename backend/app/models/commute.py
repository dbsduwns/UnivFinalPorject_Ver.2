from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CommuteProfile(Base):
    """사용자의 등교 주소와 통학 방식 설정을 저장하는 1:1 프로필."""

    __tablename__ = "commute_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # 사용자가 입력·확인한 주소와 외부 지오코딩 결과 좌표
    home_address = Column(String(255), nullable=False)
    home_road_address = Column(String(255), nullable=True)
    home_latitude = Column(Float, nullable=False)
    home_longitude = Column(Float, nullable=False)

    # 오늘의 등교 방식. 셔틀을 이용하면 기흥역 → 이공관 경로를 사용한다.
    use_shuttle = Column(Boolean, nullable=False, default=False, server_default="0")
    shuttle_destination = Column(String(100), nullable=True, default="이공관")
    departure_buffer_minutes = Column(Integer, nullable=False, default=10, server_default="10")
    # 홈 등교시간 계산 API의 사용자별 60초 재요청 제한 기준 시각
    last_home_calculation_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="commute_profile")
