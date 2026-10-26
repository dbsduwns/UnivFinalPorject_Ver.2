import httpx
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.notification_setting import NotificationSetting

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

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
    alert_type: 'notice_alert', 'shuttle_alert', 'cafeteria_alert'
    """
    query = db.query(NotificationSetting).filter(
        getattr(NotificationSetting, alert_type) == True,
        NotificationSetting.expo_push_token != None
    )
    if recipient_ids is not None:
        query = query.filter(NotificationSetting.user_id.in_(recipient_ids))
    
    settings = query.all()
    tokens = [s.expo_push_token for s in settings]

    if not tokens:
        logger.info("No opted-in push tokens for alert type: %s", alert_type)
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
