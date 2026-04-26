from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    notice_alert = Column(Boolean, default=True)
    cafeteria_alert = Column(Boolean, default=False)

    user = relationship("User", back_populates="notification_setting")