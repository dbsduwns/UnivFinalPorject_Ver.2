from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.routers.auth import verify_user_password
from app.schemas.user import PasswordVerifyRequest


def test_wrong_password_does_not_return_session_expired_status():
    user = SimpleNamespace(id=7)
    request = PasswordVerifyRequest(password="wrongpass")

    with patch("app.routers.auth.auth_service.verify_user_password", return_value=False):
        with pytest.raises(HTTPException) as error:
            verify_user_password(request, db=None, current_user=user)

    assert error.value.status_code == 400
    assert error.value.detail == "비밀번호가 일치하지 않습니다."


def test_correct_password_returns_no_content():
    user = SimpleNamespace(id=7)
    request = PasswordVerifyRequest(password="correctpass")

    with patch("app.routers.auth.auth_service.verify_user_password", return_value=True):
        response = verify_user_password(request, db=None, current_user=user)

    assert response.status_code == 204
