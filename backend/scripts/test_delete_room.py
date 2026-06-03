from app.database import SessionLocal
from app.models.chat_room import ChatRoom
from app.models.user import User
from app.services import chat as chat_service

db = SessionLocal()
try:
    user = db.query(User).get(1)
    room_id = 1
    print(f"Attempting to delete room {room_id} for user {user.id}...")
    try:
        chat_service.delete_room(db, user, room_id)
        print("Successfully deleted!")
    except ValueError as e:
        print(f"Failed: {e}")
finally:
    db.close()
