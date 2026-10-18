from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommentReportReason(str, Enum):
    ABUSE = "abuse"
    HATE = "hate"
    SEXUAL = "sexual"
    SPAM = "spam"
    PERSONAL_INFO = "personal_info"
    IMPERSONATION = "impersonation"
    ILLEGAL = "illegal"
    OTHER = "other"


class CommentReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CreateCommentReport(BaseModel):
    reason: CommentReportReason
    description: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_description(self):
        if self.description == "":
            self.description = None

        if self.reason == CommentReportReason.OTHER and not self.description:
            raise ValueError("기타 신고 사유를 입력해주세요")

        return self


class UpdateCommentReportStatus(BaseModel):
    status: CommentReportStatus
    resolution_note: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_resolution(self):
        if self.status == CommentReportStatus.PENDING:
            raise ValueError("관리자는 신고 상태를 pending으로 되돌릴 수 없습니다")

        if self.resolution_note == "":
            self.resolution_note = None

        if self.status in {
            CommentReportStatus.RESOLVED,
            CommentReportStatus.DISMISSED,
        } and not self.resolution_note:
            raise ValueError("처리 완료 또는 기각 시 처리 메모가 필요합니다")

        return self


class CommentReportResponse(BaseModel):
    id: int
    comment_id: int | None
    reason: CommentReportReason
    description: str | None
    status: CommentReportStatus
    created_at: datetime
    reviewed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminCommentReportResponse(CommentReportResponse):
    reporter_id: int | None
    reported_user_id: int | None
    content_snapshot: str
    reviewed_by_id: int | None
    resolution_note: str | None
    report_count: int = 0
    pending_report_count: int = 0
    post_id: int | None = None
    comment_is_hidden: bool | None = None
