from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserSignup, UserLogin, TokenResponse, UserResponse
from app.services import auth as auth_service
from app.models.user import User
from app.core.dependencies import get_current_user
from google.oauth2 import id_token
from google.auth.transport import requests
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