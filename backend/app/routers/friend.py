import json
import os
from html import escape
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import create_friend_invite_token, decode_friend_invite_token
from app.database import get_db
from app.models.user import User
from app.schemas.friend import (
    FriendUserResponse,
    FriendRequestsSummary,
    FriendSearchItem,
    FriendRequestCreate,
    FriendInviteLinkResponse,
    FriendInvitePreview,
    FriendTimetableResponse,
)
from app.schemas.timetable import TimetableResponse
from app.services import friend as friend_service

router = APIRouter(prefix="/api/friends", tags=["friends"])

@router.get("/search", response_model=List[FriendSearchItem])
def search_friends(
    query: str = Query(..., min_length=1, description="학번, 이름, 이메일 검색어"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """학번, 이름, 이메일로 사용자를 검색하고 현재 친구 관계 상태를 반환합니다."""
    return friend_service.search_users(db, current_user, query)

@router.post("/requests")
def send_friend_request(
    data: FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구 요청을 보냅니다 (addressee_id 또는 student_id)."""
    try:
        req = friend_service.send_friend_request(
            db,
            current_user,
            addressee_id=data.addressee_id,
            student_id=data.student_id,
        )
        return {"message": "친구 요청이 전송되었습니다.", "request_id": req.id, "status": req.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/requests", response_model=FriendRequestsSummary)
def get_friend_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청 및 보낸 친구 요청 목록을 조회합니다."""
    return friend_service.get_friend_requests(db, current_user)

@router.post("/requests/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청을 수락합니다."""
    try:
        req = friend_service.accept_friend_request(db, current_user, request_id)
        return {"message": "친구 요청을 수락했습니다.", "request_id": req.id, "status": req.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/requests/{request_id}/reject")
def reject_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청을 거절합니다."""
    try:
        friend_service.reject_friend_request(db, current_user, request_id)
        return {"message": "친구 요청을 거절했습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/requests/{request_id}")
def cancel_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보낸 친구 요청을 취소합니다."""
    try:
        friend_service.cancel_friend_request(db, current_user, request_id)
        return {"message": "보낸 친구 요청을 취소했습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[FriendUserResponse])
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """수락 완료된 내 친구 목록을 조회합니다."""
    return friend_service.get_friends(db, current_user)


@router.post("/invite-links", response_model=FriendInviteLinkResponse)
def create_friend_invite_link(
    current_user: User = Depends(get_current_user),
):
    """현재 사용자의 7일 만료 친구 초대 링크 토큰을 발급합니다."""
    token, expires_at = create_friend_invite_token(current_user.id)
    return {"token": token, "expires_at": expires_at}


@router.get("/invite/{token}", response_class=HTMLResponse, include_in_schema=False)
def open_friend_invite_link(token: str):
    """웹에서 열린 친구 초대 링크를 앱 딥링크로 전달하는 랜딩 페이지입니다."""
    inviter_id = decode_friend_invite_token(token)
    if inviter_id is None:
        return HTMLResponse(
            content="""
            <!doctype html><html lang="ko"><meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>초대 링크 만료</title>
            <body style="font-family:system-ui;padding:40px;text-align:center">
              <h1>초대 링크를 열 수 없어요</h1>
              <p>유효하지 않거나 만료된 친구 초대 링크입니다.</p>
            </body></html>
            """,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    scheme = os.getenv("APP_SCHEME", "knu")
    app_url = f"{scheme}://friends/invite?token={quote(token, safe='')}"
    download_url = os.getenv("APP_DOWNLOAD_URL", "").strip()
    app_url_js = json.dumps(app_url)
    download_url_js = json.dumps(download_url)
    download_link = (
        f'<a href="{escape(download_url, quote=True)}">앱 다운로드 페이지로 이동</a>'
        if download_url
        else "앱이 설치되어 있지 않다면 앱 설치 후 링크를 다시 열어주세요."
    )

    return HTMLResponse(
        content=f"""
        <!doctype html>
        <html lang="ko">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>KNU Campus 친구 초대</title>
            <style>
              body {{ margin:0; min-height:100vh; display:grid; place-items:center;
                background:#f4f7f8; color:#172033; font-family:system-ui,-apple-system,sans-serif; }}
              main {{ width:min(420px,calc(100% - 40px)); padding:32px 24px; box-sizing:border-box;
                border-radius:24px; background:white; text-align:center; box-shadow:0 10px 30px #17324d16; }}
              .icon {{ width:64px; height:64px; margin:0 auto 20px; display:grid; place-items:center;
                border-radius:20px; background:#e7f7fb; color:#13708d; font-size:30px; }}
              h1 {{ margin:0; font-size:22px; }} p {{ color:#7b8798; line-height:1.6; }}
              a {{ color:#13708d; font-weight:700; }}
              button {{ width:100%; margin-top:18px; border:0; border-radius:14px; padding:14px;
                background:#13708d; color:white; font-size:15px; font-weight:700; }}
            </style>
          </head>
          <body>
            <main>
              <div class="icon">👥</div>
              <h1>KNU Campus 친구 초대</h1>
              <p id="message">앱에서 친구 초대 화면을 여는 중이에요.</p>
              <button type="button" onclick="openApp()">앱에서 초대 수락하기</button>
              <p id="fallback">{download_link}</p>
            </main>
            <script>
              const appUrl = {app_url_js};
              const downloadUrl = {download_url_js};
              const message = document.getElementById("message");

              function openApp() {{
                const startedAt = Date.now();
                window.location.href = appUrl;
                window.setTimeout(() => {{
                  if (document.visibilityState === "visible" && Date.now() - startedAt >= 1200) {{
                    message.textContent = downloadUrl
                      ? "앱이 열리지 않았어요. 앱을 설치한 뒤 다시 시도해주세요."
                      : "앱이 설치되어 있지 않은 것 같아요.";
                    if (downloadUrl) window.location.href = downloadUrl;
                  }}
                }}, 1400);
              }}

              if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
                window.setTimeout(openApp, 250);
              }}
            </script>
          </body>
        </html>
        """,
    )


@router.get("/invite-links/{token}", response_model=FriendInvitePreview)
def get_friend_invite_link(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """초대 링크를 미리 보고 초대한 사용자와 현재 관계를 확인합니다."""
    inviter_id = decode_friend_invite_token(token)
    if inviter_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않거나 만료된 초대 링크입니다.")
    try:
        return friend_service.get_friend_invite_preview(db, current_user, inviter_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/invite-links/{token}/accept")
def accept_friend_invite_link(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """초대 링크를 수락하고 두 사용자를 친구로 연결합니다."""
    inviter_id = decode_friend_invite_token(token)
    if inviter_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않거나 만료된 초대 링크입니다.")
    try:
        friendship = friend_service.accept_friend_invite(db, current_user, inviter_id)
        return {"message": "친구 초대를 수락했습니다.", "friendship_id": friendship.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{friend_id}")
def delete_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구 관계를 해제(삭제)합니다."""
    try:
        friend_service.delete_friend(db, current_user, friend_id)
        return {"message": "친구 관계가 해제되었습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{friend_id}/timetables", response_model=List[TimetableResponse])
def get_friend_timetables(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구의 시간표 목록을 조회합니다 (친구 관계 검증 필수)."""
    try:
        return friend_service.get_friend_timetables(db, current_user, friend_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/{friend_id}/timetable", response_model=FriendTimetableResponse)
def get_friend_timetable_detail(
    friend_id: int,
    timetable_id: Optional[int] = Query(None, description="특정 시간표 ID (생략 시 대표 시간표)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구의 시간표 상세 정보(강의 및 일정 포함)를 조회합니다 (친구 관계 검증 필수)."""
    try:
        return friend_service.get_friend_timetable_detail(
            db, current_user, friend_id, timetable_id=timetable_id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
