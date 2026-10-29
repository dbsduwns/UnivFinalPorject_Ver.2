from sqlalchemy import Column, DateTime, Integer, String, func

from app.database import Base


class PasswordResetRequestLog(Base):
    __tablename__ = "password_reset_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_hash = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
