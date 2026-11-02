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
from app.models.user_presence import UserPresence
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatRoomResponse, MessengerRoomCreate
from app.services import chat


class FriendChatTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for table in (User.__table__, Friendship.__table__, RoomMessenger.__table__, RoomParticipant.__table__, Messenger.__table__, UserPresence.__table__):
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

    def test_group_message_unread_count_decreases_as_members_read(self):
        alice, bob, carol, _ = self.users
        group = chat.create_room(self.db, alice, MessengerRoomCreate(participant_ids=[bob.id, carol.id]))
        message = chat.send_message(self.db, alice, group.id, ChatMessageCreate(content="hello"))

        self.assertEqual(ChatMessageResponse.model_validate(message).unread_count, 2)
        self.assertEqual(chat.get_room_messages(self.db, alice, group.id)[0].unread_count, 2)
        self.assertEqual(chat.get_room_messages(self.db, bob, group.id)[0].unread_count, 1)
        self.assertEqual(chat.get_room_messages(self.db, carol, group.id)[0].unread_count, 0)
        self.assertEqual(chat.get_my_rooms(self.db, bob)[0].unread_count, 0)

    @patch("app.services.chat.notify_users_by_type_sync")
    def test_direct_message_unread_count_reaches_zero_after_read(self, notify):
        alice, bob, _, _ = self.users
        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        message = chat.send_message(self.db, alice, direct.id, ChatMessageCreate(content="hello"))

        self.assertEqual(message.unread_count, 1)
        self.assertEqual(chat.get_my_rooms(self.db, bob)[0].unread_count, 1)
        self.assertEqual(chat.get_room_messages(self.db, bob, direct.id)[0].unread_count, 0)
        self.assertEqual(chat.get_room_messages(self.db, alice, direct.id)[0].unread_count, 0)

    def test_group_room_name_and_notification_settings_are_per_participant(self):
        alice, bob, carol, _ = self.users
        group = chat.create_room(self.db, alice, MessengerRoomCreate(participant_ids=[bob.id, carol.id]))

        renamed = chat.update_room_name(self.db, bob, group.id, "캡스톤 팀")
        self.assertEqual(renamed.name, "캡스톤 팀")
        muted = chat.update_room_notification(self.db, bob, group.id, True)
        self.assertTrue(muted.is_muted)

        bob_room = next(room for room in chat.get_my_rooms(self.db, bob) if room.id == group.id)
        self.assertTrue(bob_room.is_muted)
        carol_room = next(room for room in chat.get_my_rooms(self.db, carol) if room.id == group.id)
        self.assertFalse(carol_room.is_muted)

        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        with self.assertRaises(ValueError):
            chat.update_room_name(self.db, alice, direct.id, "변경 불가")

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
            {
                "type": "direct_message",
                "room_id": direct.id,
                "sender_id": alice.id,
                "recipient_id": bob.id,
            },
            recipient_ids=[bob.id],
        )

    @patch("app.services.chat.notify_users_by_type_sync")
    def test_muted_direct_room_does_not_notify_recipient(self, notify):
        alice, bob, _, _ = self.users
        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        chat.update_room_notification(self.db, bob, direct.id, True)

        chat.send_message(self.db, alice, direct.id, ChatMessageCreate(content="muted message"))

        notify.assert_not_called()

    @patch("app.services.chat.notify_users_by_type_sync")
    def test_viewing_direct_room_does_not_notify_recipient(self, notify):
        alice, bob, _, _ = self.users
        direct = chat.create_room(self.db, alice, MessengerRoomCreate(friend_id=bob.id))
        self.db.add(UserPresence(
            user_id=bob.id,
            active_room_id=direct.id,
            is_app_foreground=True,
        ))
        self.db.commit()

        chat.send_message(self.db, alice, direct.id, ChatMessageCreate(content="already viewing"))

        notify.assert_not_called()

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
