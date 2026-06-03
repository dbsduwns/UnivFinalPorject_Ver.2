import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.chat_room import ChatRoom

# Manually set DATABASE_URL if needed or use what's in app.database
from app.database import SessionLocal

db = SessionLocal()
try:
    print("--- Users ---")
    users = db.query(User).all()
    for u in users:
        # Check if 'name' exists
        name = getattr(u, 'name', 'N/A')
        print(f"ID: {u.id}, Email: {u.email}, Name: {name}")

    print("\n--- Chat Rooms ---")
    rooms = db.query(ChatRoom).all()
    for r in rooms:
        print(f"ID: {r.id}, User ID: {r.user_id}, Title: {r.title}")
finally:
    db.close()
