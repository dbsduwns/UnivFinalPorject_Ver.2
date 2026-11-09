import httpx
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.notification_setting import NotificationSetting
from app.models.user_notification import UserNotification

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def save_in_app_notifications(
    db: Session,
    settings: list[NotificationSetting],
    title: str,
    body: str,
    data: Dict[str, Any] | None = None,
) -> None:
    if not settings:
        return

    notification_data = dict(data or {})
    notification_type = str(notification_data.get("type") or "notification")
    try:
        db.add_all([
            UserNotification(
                user_id=setting.user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                data=dict(notification_data),
            )
            for setting in settings
        ])
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to save in-app notifications")

async def send_push_notification(tokens: List[str], title: str, body: str, data: Dict[str, Any] = None):
    if not tokens:
        return

    messages = []
    for token in tokens:
        # Expo SDK/서비스 버전에 따라 두 형식 모두 발급될 수 있습니다.
        if not token.startswith(("ExpoPushToken[", "ExponentPushToken[")):
            logger.warning("Ignoring an invalid Expo push token format")
            continue
        
        message = {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
        }
        if data:
            message["data"] = data
        messages.append(message)

    if not messages:
        return

    # Push token은 개인정보·자격증명 성격이 있으므로 로그에 남기지 않고,
    # 실제 전송 대상 수와 앱이 수신할 data payload만 기록한다.
    logger.info(
        "[Push] Expo payload prepared: recipient_count=%d title=%r body=%r data=%s",
        len(messages),
        title,
        body,
        data or {},
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(EXPO_PUSH_URL, json=messages)
            response.raise_for_status()
            result = response.json()
            failed_tickets = [
                ticket for ticket in result.get("data", []) if ticket.get("status") != "ok"
            ]
            if failed_tickets:
                logger.error("Expo push notification rejected: %s", failed_tickets)
                return None
            logger.info(f"Push notification sent successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return None

async def notify_users_by_type(
    db: Session,
    alert_type: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    recipient_ids: List[int] | None = None,
):
    """
    alert_type: 'notice_alert', 'shuttle_alert', 'cafeteria_alert', 'message_alert'
    """
    alert_setting = getattr(NotificationSetting, alert_type, None)
    if alert_setting is None:
        raise ValueError(f"지원하지 않는 알림 유형입니다: {alert_type}")

    query = db.query(NotificationSetting).filter(alert_setting.is_(True))
    if recipient_ids is not None:
        query = query.filter(NotificationSetting.user_id.in_(recipient_ids))
    
    settings = query.all()
    notification_data = dict(data or {})
    notification_data.setdefault("type", alert_type)
    save_in_app_notifications(db, settings, title, body, notification_data)

    tokens = [s.expo_push_token for s in settings if s.expo_push_token]

    if not tokens:
        logger.info(
            "Saved %s in-app notification(s); no push tokens for alert type: %s",
            len(settings),
            alert_type,
        )
        return None

    logger.info("Sending %s push notification(s) for alert type: %s", len(tokens), alert_type)
    return await send_push_notification(tokens, title, body, data)

def notify_users_by_type_sync(
    db: Session,
    alert_type: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    recipient_ids: List[int] | None = None,
):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # 이미 루프가 실행 중인 경우 (FastAPI 요청 중 등)
        import threading
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(
                notify_users_by_type(db, alert_type, title, body, data, recipient_ids)
            )
            new_loop.close()
        threading.Thread(target=run_in_new_loop).start()
    else:
        loop.run_until_complete(
            notify_users_by_type(db, alert_type, title, body, data, recipient_ids)
        )
