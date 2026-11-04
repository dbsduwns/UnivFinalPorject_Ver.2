import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import (
    UserSignup, UserLogin, TokenResponse, UserResponse, UserUpdate,
    PasswordResetConfirm, PasswordResetRequest,
    PushTokenUpdate, NotificationSettingResponse, NotificationSettingUpdate
)
from app.services import auth as auth_service
from app.services import google_auth as google_auth_service
from app.services import student_verification as student_verification_service
from app.services import account as account_service
from app.services import password_reset as password_reset_service
from app.schemas.user import PasswordVerifyRequest, PasswordChangeRequest
from app.models.user import User
from app.models.notification_setting import NotificationSetting
from app.models.refresh_session import RefreshSession
from app.core.dependencies import get_current_user
from app.core.notification import send_push_notification
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_jti
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str

class GoogleLoginRequest(BaseModel):
    id_token: str


class StudentVerificationConfirmRequest(BaseModel):
    verification_id: int = Field(gt=0)
    onboarding_token: str = Field(min_length=20, max_length=256)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class StudentVerificationRequest(BaseModel):
    onboarding_token: str = Field(min_length=20, max_length=256)
    student_email: str = Field(min_length=5, max_length=320)

@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다. 다시 로그인해주세요.")

    required_claims = ("sub", "token_version", "session_id", "jti")
    if any(not payload.get(claim) for claim in required_claims):
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다. 다시 로그인해주세요.")

    session = db.query(RefreshSession).filter(
        RefreshSession.session_id == payload["session_id"]
    ).with_for_update().first()

    if session is None or session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="리프레시 세션이 존재하지 않거나 만료되었습니다. 다시 로그인해주세요.")
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="리프레시 세션이 만료되었습니다. 다시 로그인해주세요.")

    if hash_jti(payload["jti"]) != session.current_jti_hash:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="리프레시 세션이 만료되었습니다. 다시 로그인해주세요.")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다. 다시 로그인해주세요.")

    new_jti = secrets.token_urlsafe(32)

    session.current_jti_hash = hash_jti(new_jti)
    session.last_used_at = datetime.now(timezone.utc)

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active or user.token_version != payload["token_version"]:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다. 다시 로그인해주세요.")

    new_refresh_token = create_refresh_token({
        "sub": str(user.id),
        "token_version": user.token_version,
        "session_id": session.session_id,
        "jti": new_jti,
    })

    new_access_token = create_access_token({
        "sub": str(user.id),
        "token_version": user.token_version,
    })

    db.commit()

    return RefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke the refresh session associated with the current refresh token."""
    payload = decode_token(data.refresh_token)
    if payload is not None and payload.get("type") == "refresh":
        session_id = payload.get("session_id")
        if session_id:
            session = db.query(RefreshSession).filter(
                RefreshSession.session_id == session_id,
            ).first()
            if session is not None and session.revoked_at is None:
                session.revoked_at = datetime.now(timezone.utc)
                db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-password", status_code=status.HTTP_204_NO_CONTENT)
def verify_user_password(
    data: PasswordVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not auth_service.verify_user_password(db, current_user.id, data.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="비밀번호가 일치하지 않습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        auth_service.change_user_password(
            db,
            current_user,
            data.current_password,
            data.new_password,
            data.confirm_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
@router.post("/signup", response_model=UserResponse)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    try:
        return auth_service.signup(db, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

@router.post("/google")
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    return google_auth_service.authenticate_google_user(db, data.id_token)

@router.post("/student-verification/confirm")
def confirm_student_verification(data: StudentVerificationConfirmRequest, db: Session = Depends(get_db)):
    try:
        return student_verification_service.confirm_student_verification(
            db,
            verification_id=data.verification_id,
            onboarding_token=data.onboarding_token,
            input_otp=data.otp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/student-verification/request", status_code=status.HTTP_202_ACCEPTED)
def request_student_verification(
    data: StudentVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        result = student_verification_service.request_student_verification(
            db,
            data.onboarding_token,
            data.student_email,
        )
        return {
            "status": "verification_code_sent",
            **result,
        }
    except student_verification_service.StudentVerificationRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        return auth_service.login(db, data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    try:
        password_reset_service.request_password_reset(db, data.email, client_ip)
    except password_reset_service.PasswordResetRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return {"message": "입력한 이메일이 등록되어 있다면 비밀번호 재설정 안내를 발송했습니다."}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        password_reset_service.confirm_password_reset(
            db,
            data.token,
            data.new_password,
            data.confirm_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/me", response_model=UserResponse)
def me(current_user: User= Depends(get_current_user)):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 회원 계정과 회원이 생성한 데이터를 영구 삭제한다."""
    try:
        account_service.delete_account(db, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="회원 탈퇴 처리에 실패했습니다.") from exc

@router.put("/update", response_model=UserResponse)
def update_profile(
    data: UserUpdate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if data.name: current_user.name = data.name
        if data.department: current_user.department = data.department
        if data.grade is not None: current_user.grade = data.grade
        
        if data.student_id:
            # 중복 체크
            existing = db.query(User).filter(User.student_id == data.student_id, User.id != current_user.id).first()
            if existing:
                raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")
            current_user.student_id = data.student_id
            
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/notification-token")
async def update_notification_token(
    data: PushTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    setting = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()

    if not setting:
        setting = NotificationSetting(user_id=current_user.id, expo_push_token=data.expo_push_token)
        db.add(setting)
    else:
        setting.expo_push_token = data.expo_push_token
    
    db.commit()
    return {"message": "푸시 토큰이 성공적으로 업데이트 되었습니다."}


@router.post("/notification-test")
async def send_notification_test(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """현재 로그인한 회원의 기기로만 테스트 푸시를 전송한다."""
    setting = (
        db.query(NotificationSetting)
        .filter(NotificationSetting.user_id == current_user.id)
        .first()
    )
    if not setting or not setting.expo_push_token:
        raise HTTPException(
            status_code=409,
            detail="등록된 푸시 토큰이 없습니다. 앱 알림 권한을 확인해주세요.",
        )

    result = await send_push_notification(
        [setting.expo_push_token],
        "🔔 KNU Campus 푸시 알림 테스트",
        "푸시 알림이 정상적으로 연결되었습니다.",
        {"type": "notification_test"},
    )
    if result is None:
        raise HTTPException(status_code=502, detail="푸시 알림 전송에 실패했습니다.")
    return {"message": "테스트 푸시 전송 요청이 완료되었습니다.", "result": result}

@router.get("/notification-settings", response_model=NotificationSettingResponse)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    setting = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()
    if not setting:
        setting = NotificationSetting(user_id=current_user.id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

@router.put("/notification-settings", response_model=NotificationSettingResponse)
def update_notification_settings(
    data: NotificationSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    setting = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()
    if not setting:
        setting = NotificationSetting(user_id=current_user.id)
        db.add(setting)
    
    if data.notice_alert is not None: setting.notice_alert = data.notice_alert
    if data.cafeteria_alert is not None: setting.cafeteria_alert = data.cafeteria_alert
    if data.shuttle_alert is not None: setting.shuttle_alert = data.shuttle_alert
    if data.message_alert is not None: setting.message_alert = data.message_alert
    
    db.commit()
    db.refresh(setting)
    return setting
