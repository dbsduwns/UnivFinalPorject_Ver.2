from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(255), unique=True, nullable=False)
    board_slug = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(1024), nullable=True)
    image_path = Column(String(512), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, server_default="false", nullable=False)
    is_pinned = Column(Boolean, default=False, server_default="false", nullable=False)
    author = relationship("User", foreign_keys=[author_id])

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
