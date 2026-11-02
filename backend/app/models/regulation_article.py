from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class RegulationArticle(Base):
    __tablename__ = "regulation_articles"

    id = Column(Integer, primary_key=True)
    source_key = Column(String(80), nullable=False, unique=True)
    rule_title = Column(String(300), nullable=False)
    article_heading = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    source_url = Column(Text, nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=False)
