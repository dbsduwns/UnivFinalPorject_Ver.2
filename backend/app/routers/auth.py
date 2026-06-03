from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import (
    UserSignup, UserLogin, TokenResponse, UserResponse, UserUpdate, 
    PushTokenUpdate, NotificationSettingResponse, NotificationSettingUpdate
)
from app.services import auth as auth_service
from app.models.user import User
from app.models.notification_setting import NotificationSetting
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    try:
        return auth_service.signup(db, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

@router.post("/google")
async def google_login(data: dict, db: Session = Depends(get_db)):
    token = data.get("id_token")
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), "433369528179-1ra3pg4pffr7iuupnabdnk588c0q1tga.apps.googleusercontent.com")

        email = idinfo['email'],
        name = idinfo.get('name', 'Google User')

        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name, hashed_password="google_authenticated")
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    
@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        return auth_service.login(db, data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

@router.get("/me", response_model=UserResponse)
def me(current_user: User= Depends(get_current_user)):
    return current_user

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
    
    db.commit()
    db.refresh(setting)
    return setting