import os
import argparse
import sys
from pathlib import Path
from sqlalchemy import func


# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.user import User



def promote_admin(user_email: str):
    db = SessionLocal()

    try:
        normalized_email = user_email.strip().lower()

        user = (
            db.query(User)
            .filter(func.lower(User.email) == normalized_email)
            .first()
        )

        if user is None:
            print(f"사용자를 찾을 수 없습니다: {user_email}")
            return False
        if user.is_admin:
            print(f"이미 관리자입니다: {user_email}")
            return True

        user.is_admin = True

        db.commit()
        db.refresh(user)

        print(f"관리자 권한을 부여했습니다: {user.email}")
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="기존 사용자에게 관리자 권한을 부여합니다."
    )
    parser.add_argument("email", help="관리자로 지정할 사용자 이메일")
    args = parser.parse_args()

    success = promote_admin(args.email)
    raise SystemExit(0 if success else 1)