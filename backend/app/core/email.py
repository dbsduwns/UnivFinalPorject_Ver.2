import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")
PASSWORD_RESET_URL = os.getenv("PASSWORD_RESET_URL")

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

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError("비밀번호 재설정 이메일 발송에 실패했습니다.") from exc
