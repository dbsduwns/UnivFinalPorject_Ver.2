from pydantic import BaseModel, ConfigDict

class PostLikeResponse(BaseModel):
    id: int
    user_id: int
    post_id: int

    model_config = ConfigDict(from_attributes=True)

class CommentLikeResponse(BaseModel):
    id: int
    user_id: int
    comment_id: int

    model_config = ConfigDict(from_attributes=True)