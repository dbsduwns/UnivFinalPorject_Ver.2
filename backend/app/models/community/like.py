from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base

class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    __table_args__ =(
        UniqueConstraint("user_id", "post_id"),
    )

class CommentLike(Base):
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id"),
    )
