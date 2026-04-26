from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_menu_id = Column(Integer, ForeignKey("daily_menus.id"))
    name = Column(String(200), nullable=False)
    price = Column(Integer)
    calories = Column(Integer)

    daily_menu = relationship("DailyMenu", back_populates="menu_items")