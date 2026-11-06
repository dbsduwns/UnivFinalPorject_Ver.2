import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.notification import save_in_app_notifications
from app.models.notification_setting import NotificationSetting
from app.models.user import User
from app.models.user_notification import UserNotification
from app.routers.notification import (
    get_notifications,
    get_unread_notification_count,
    read_all_notifications,
    read_notification,
)


class NotificationCenterTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for table in (User.__table__, NotificationSetting.__table__, UserNotification.__table__):
            table.create(self.engine)
        self.db = Session(self.engine)
        self.user = User(
            email="notice@example.com",
            password_hash="hash",
            name="알림 사용자",
            is_active=True,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.db.add(NotificationSetting(user_id=self.user.id, notice_alert=True))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_in_app_notification_is_saved_without_push_token(self):
        settings = self.db.query(NotificationSetting).all()
        save_in_app_notifications(
            self.db,
            settings,
            "새 공지",
            "공지 본문",
            {"type": "notice", "notice_id": 42},
        )

        response = get_notifications(
            limit=100,
            offset=0,
            db=self.db,
            current_user=self.user,
        )
        self.assertEqual(response.unread_count, 1)
        self.assertEqual(response.items[0].data["notice_id"], 42)

    def test_read_one_and_read_all_only_update_current_user(self):
        first = UserNotification(
            user_id=self.user.id,
            notification_type="notice",
            title="첫 알림",
            body="본문",
            data={},
        )
        second = UserNotification(
            user_id=self.user.id,
            notification_type="shuttle",
            title="두 번째 알림",
            body="본문",
            data={},
        )
        self.db.add_all([first, second])
        self.db.commit()
        self.db.refresh(first)

        response = read_notification(first.id, db=self.db, current_user=self.user)
        self.assertIsNotNone(response.read_at)
        self.assertEqual(
            get_unread_notification_count(db=self.db, current_user=self.user)["unread_count"],
            1,
        )

        response = read_all_notifications(db=self.db, current_user=self.user)
        self.assertEqual(response["updated_count"], 1)
        self.assertEqual(
            get_notifications(limit=100, offset=0, db=self.db, current_user=self.user).unread_count,
            0,
        )

    def test_cannot_read_another_users_notification(self):
        other = User(
            email="other@example.com",
            password_hash="hash",
            name="다른 사용자",
            is_active=True,
        )
        self.db.add(other)
        self.db.commit()
        self.db.refresh(other)
        notification = UserNotification(
            user_id=other.id,
            notification_type="notice",
            title="다른 사용자 알림",
            body="본문",
            data={},
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        with self.assertRaises(HTTPException) as raised:
            read_notification(notification.id, db=self.db, current_user=self.user)
        self.assertEqual(raised.exception.status_code, 404)
