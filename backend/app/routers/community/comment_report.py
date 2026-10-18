from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin_user, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.community import (
    AdminCommentReportResponse,
    CommentReportResponse,
    CreateCommentReport,
    UpdateCommentReportStatus,
)
from app.services.community import comment_report as comment_report_service


router = APIRouter(prefix="/api/community", tags=["community"])
admin_router = APIRouter(prefix="/api/admin/comment-reports", tags=["admin"])


@router.get("/my-comment-reports", response_model=list[CommentReportResponse])
def get_my_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.community.comment_report import CommentReport
    return db.query(CommentReport).filter(CommentReport.reporter_id == user.id).order_by(
        CommentReport.created_at.desc(), CommentReport.id.desc()
    ).offset(skip).limit(limit).all()


@router.post(
    "/commentreports",
    response_model=CommentReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment_report(
    comment_id: int,
    data: CreateCommentReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return comment_report_service.create_comment_report(
            db,
            current_user,
            comment_id,
            data,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@admin_router.get("", response_model=list[AdminCommentReportResponse])
def get_comment_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return comment_report_service.get_comment_reports(db, skip, limit)


@admin_router.get("/{report_id}", response_model=AdminCommentReportResponse)
def get_comment_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    report = comment_report_service.get_comment_report_by_id(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신고 내역을 찾을 수 없습니다",
        )
    return report


@admin_router.patch("/{report_id}", response_model=AdminCommentReportResponse)
def update_comment_report_status(
    report_id: int,
    data: UpdateCommentReportStatus,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    try:
        return comment_report_service.update_comment_report_status(
            db,
            current_admin,
            report_id,
            data,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
