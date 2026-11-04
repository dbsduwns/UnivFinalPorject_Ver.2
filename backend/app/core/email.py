import os
import smtplib
import ssl
import logging
from email.message import EmailMessage
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")
PASSWORD_RESET_URL = os.getenv("PASSWORD_RESET_URL")


def _send_smtp_message(message: EmailMessage) -> None:
    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM]):
        logger.error("SMTP email configuration is incomplete")
        raise RuntimeError("이메일 발송 설정이 완료되지 않았습니다.")

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("SMTP email delivery failed")
        raise RuntimeError("이메일 발송에 실패했습니다.") from exc

def send_password_reset_email(email: str, raw_token: str) -> None:
    if not all(
        [
            SMTP_HOST,
            SMTP_USERNAME,
            SMTP_PASSWORD,
            SMTP_FROM,
            PASSWORD_RESET_URL,
        ]
    ):
        logger.error("Password reset email configuration is incomplete")
        raise RuntimeError("이메일 발송에 문제가 생겼습니다.")

    query = urlencode({"token": raw_token})
    reset_url = f"{PASSWORD_RESET_URL}?{query}"

    message = EmailMessage()
    message["Subject"] = "[KNU CAMPUS] 비밀번호 재설정 안내"
    message["From"] = SMTP_FROM
    message["To"] = email

    message.set_content(
        f"""안녕하세요.
        
        비밀번호 재설정 요청이 접수되었습니다.
        아래 링크에서 새 비밀번호를 설정해 주세요.
        
        {reset_url}

        이 링크는 15분 동안만 유효하니, 15분 안에 재설정을 마쳐야합니다.
        본인이 요청하지 않았다면 이 이메일을 무시해 주세요.
        """
    )

    _send_smtp_message(message)
    logger.info("Password reset email accepted by SMTP server")


def send_student_verification_email(email: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "[KNU CAMPUS] 학생 인증 코드"
    message["From"] = SMTP_FROM or ""
    message["To"] = email
    message.set_content(
        f"""안녕하세요.

KNU Campus 학생 인증 코드입니다.

인증 코드: {otp}

이 코드는 10분 동안만 유효합니다.
본인이 요청하지 않았다면 이 이메일을 무시해 주세요.
"""
    )
    _send_smtp_message(message)
    logger.info("Student verification email accepted by SMTP server")
