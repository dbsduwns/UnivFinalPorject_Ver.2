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
        if not token.startswith("ExponentPushToken"):
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
            logger.info(f"Push notification sent successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return None

async def notify_users_by_type(db: Session, alert_type: str, title: str, body: str, data: Dict[str, Any] = None):
    """
    alert_type: 'notice_alert', 'shuttle_alert', 'cafeteria_alert'
    """
    query = db.query(NotificationSetting).filter(
        getattr(NotificationSetting, alert_type) == True,
        NotificationSetting.expo_push_token != None
    )
    
    settings = query.all()
    tokens = [s.expo_push_token for s in settings]
    
    if tokens:
        await send_push_notification(tokens, title, body, data)

def notify_users_by_type_sync(db: Session, alert_type: str, title: str, body: str, data: Dict[str, Any] = None):
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
            new_loop.run_until_complete(notify_users_by_type(db, alert_type, title, body, data))
            new_loop.close()
        threading.Thread(target=run_in_new_loop).start()
    else:
        loop.run_until_complete(notify_users_by_type(db, alert_type, title, body, data))
