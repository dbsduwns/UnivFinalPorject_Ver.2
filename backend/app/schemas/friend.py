from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.timetable import TimetableDetailResponse, TimetableResponse

class FriendUserResponse(BaseModel):
    id: int
    email: str
    name: str
    student_id: Optional[str] = None
    department: Optional[str] = None
    grade: Optional[int] = None
    avatar_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class FriendRequestCreate(BaseModel):
    addressee_id: Optional[int] = None
    student_id: Optional[str] = None

class FriendshipRequestItem(BaseModel):
    id: int
    status: str
    created_at: Optional[datetime] = None
    user: FriendUserResponse  # 상대방 유저 정보

    model_config = {
        "from_attributes": True
    }

class FriendRequestsSummary(BaseModel):
    received: List[FriendshipRequestItem] = []
    sent: List[FriendshipRequestItem] = []

class FriendSearchItem(BaseModel):
    user: FriendUserResponse
    friendship_status: str  # "NONE", "PENDING_SENT", "PENDING_RECEIVED", "FRIEND"
    request_id: Optional[int] = None

class FriendTimetableResponse(BaseModel):
    friend: FriendUserResponse
    timetable: Optional[TimetableDetailResponse] = None
    available_timetables: List[TimetableResponse] = []
