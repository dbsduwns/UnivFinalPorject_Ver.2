import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.friendship import Friendship
from app.models.messenger import Messenger
from app.models.room_messengers import RoomMessenger
from app.models.room_participants import RoomParticipant
from app.models.user import User
from app.schemas.chat import ChatMessageCreate, ChatRoomResponse, MessengerRoomCreate
from app.services import chat


class FriendChatTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for table in (User.__table__, Friendship.__table__, RoomMessenger.__table__, RoomParticipant.__table__, Messenger.__table__):
            table.create(self.engine)
        self.db = Session(self.engine)
        self.users = [
            User(email=f"user{number}@example.com", password_hash="test", name=f"User {number}", is_active=True)
            for number in range(1, 5)
        ]
        self.db.add_all(self.users)
        self.db.commit()
        for user in self.users:
            self.db.refresh(user)
        self.db.add_all([
            Friendship(requester_id=self.users[0].id, addressee_id=user.id, status="ACCEPTED")
            for user in self.users[1:3]
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_direct_and_group_rooms_and_access(self):
        alice, bob, carol, outsider = self.users
        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        same_direct = chat.create_room(self.db, bob, MessengerRoomCreate(friend_id=alice.id))
        self.assertEqual(direct.id, same_direct.id)
        self.assertFalse(direct.is_group)

        group = chat.create_room(self.db, alice, MessengerRoomCreate(participant_ids=[bob.id, carol.id], name="Study"))
        self.assertTrue(group.is_group)
        self.assertNotEqual(direct.id, group.id)
        self.assertEqual(len(ChatRoomResponse.model_validate(group).participants), 3)
        self.assertEqual({room.id for room in chat.get_my_rooms(self.db, bob)}, {direct.id, group.id})
        self.assertIsNone(chat.get_my_room(self.db, outsider, group.id))

        message = chat.send_message(self.db, bob, group.id, ChatMessageCreate(content="hello"))
        self.assertEqual(message.sender_id, bob.id)
        self.assertEqual([item.id for item in chat.get_room_messages(self.db, carol, group.id)], [message.id])
        with self.assertRaises(ValueError):
            chat.send_message(self.db, outsider, group.id, ChatMessageCreate(content="blocked"))

    def test_group_leave_does_not_delete_other_members_messages(self):
        alice, bob, carol, _ = self.users
        group = chat.create_room(self.db, alice, MessengerRoomCreate(participant_ids=[bob.id, carol.id]))
        chat.send_message(self.db, alice, group.id, ChatMessageCreate(content="hello"))
        chat.delete_room(self.db, bob, group.id)
        self.assertIsNone(chat.get_my_room(self.db, bob, group.id))
        self.assertEqual(len(chat.get_room_messages(self.db, carol, group.id)), 1)

    @patch("app.services.chat.notify_users_by_type_sync")
    def test_direct_message_notifies_only_the_recipient(self, notify):
        alice, bob, _, _ = self.users
        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))

        chat.send_message(self.db, alice, direct.id, ChatMessageCreate(content="private message"))

        notify.assert_called_once_with(
            self.db,
            "message_alert",
            "User 1님이 메시지를 보냈습니다.",
            "새 메시지가 도착했습니다.",
            {"type": "direct_message", "room_id": direct.id},
            recipient_ids=[bob.id],
        )

    def test_non_friend_cannot_create_room_and_direct_leave_allows_new_room(self):
        alice, bob, _, outsider = self.users
        with self.assertRaises(PermissionError):
            chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=outsider.id))

        original = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        chat.delete_room(self.db, bob, original.id)
        with self.assertRaises(ValueError):
            chat.send_message(self.db, alice, original.id, ChatMessageCreate(content="hello"))

        replacement = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        self.assertNotEqual(original.id, replacement.id)


if __name__ == "__main__":
    unittest.main()
