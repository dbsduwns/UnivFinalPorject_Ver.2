from app.database import SessionLocal
from app.models.chat_room import ChatRoom
from app.models.user import User

db = SessionLocal()
try:
    print("--- Users ---")
    users = db.query(User).all()
    for u in users:
        print(f"ID: {u.id}, Email: {u.email}")

    print("\n--- Chat Rooms ---")
    rooms = db.query(ChatRoom).all()
    for r in rooms:
        print(f"ID: {r.id}, User ID: {r.user_id}, Title: {r.title}")
finally:
    db.close()
