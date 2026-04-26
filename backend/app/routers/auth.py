from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserSignup, UserLogin, TokenResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/signup")
def signup(data: UserSignup, db: Session = Depends(get_db)):
    try:
        user = auth_service.signup(db, data)
        return {"message": "회원가입이 완료되었습니다"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = auth_service.login(db, data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    