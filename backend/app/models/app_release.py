from sqlalchemy import Boolean, Column, Integer, JSON, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class AppRelease(Base):
    __tablename__ = "app_releases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True)
    version_code = Column(Integer, nullable=False)
    version_name = Column(String(50), nullable=False)
    minimum_version_code = Column(Integer, nullable=False, default=1, server_default="1")
    apk_url = Column(String(2048), nullable=False)
    sha256 = Column(String(64), nullable=True)
    release_notes = Column(JSON, nullable=False, default=list)
    mandatory = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("platform", "version_code", name="uq_app_releases_platform_version_code"),
    )
