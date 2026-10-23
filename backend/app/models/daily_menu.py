from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class DailyMenu(Base):
    __tablename__ = "daily_menus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_date = Column(Date, nullable=False)
    image_url = Column(String)
    image_sha256 = Column(String(64))
    ocr_status = Column(String(20), nullable=False, default="pending")
    ocr_error = Column(Text)
    crawled_at = Column(TIMESTAMP, server_default=func.now())

    # 동일한 날짜에 중복 식단 방지
    __table_args__ = (UniqueConstraint('menu_date', name='_menu_date_uc'),)

    menu_items = relationship(
        "MenuItem",
        back_populates="daily_menu",
        cascade="all, delete-orphan",
    )
