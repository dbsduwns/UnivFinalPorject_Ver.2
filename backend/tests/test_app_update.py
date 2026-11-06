import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.app_release import AppRelease
from app.routers.app_update import (
    check_android_update,
    create_app_release,
    update_app_release,
)
from app.schemas.app_update import AppReleaseCreate, AppReleaseUpdate


class AppUpdateTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AppRelease.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.admin = SimpleNamespace(id=1, is_admin=True)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_release(
        self,
        version_code: int,
        *,
        minimum_version_code: int = 1,
        mandatory: bool = False,
        is_active: bool = True,
    ):
        return create_app_release(
            AppReleaseCreate(
                version_code=version_code,
                version_name=f"1.{version_code}.0",
                minimum_version_code=minimum_version_code,
                apk_url=f"https://downloads.example.com/knu-{version_code}.apk",
                release_notes=[f"버전 {version_code}"],
                mandatory=mandatory,
                is_active=is_active,
            ),
            db=self.db,
            current_admin=self.admin,
        )

    def test_update_check_uses_active_latest_release(self):
        first = self.create_release(2, minimum_version_code=2)

        required = check_android_update(current_version_code=1, db=self.db)
        self.assertTrue(required.update_available)
        self.assertTrue(required.mandatory)
        self.assertEqual(required.latest_release.id, first.id)

        current = check_android_update(current_version_code=2, db=self.db)
        self.assertFalse(current.update_available)
        self.assertFalse(current.mandatory)

        second = self.create_release(3)
        self.db.refresh(first)
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(
            check_android_update(current_version_code=2, db=self.db).latest_release.id,
            second.id,
        )

    def test_release_can_be_activated_and_forced(self):
        release = self.create_release(4, is_active=False)
        updated = update_app_release(
            release.id,
            AppReleaseUpdate(is_active=True, mandatory=True, minimum_version_code=3),
            db=self.db,
            current_admin=self.admin,
        )
        self.assertTrue(updated.is_active)
        self.assertTrue(updated.mandatory)
        self.assertIsNotNone(updated.published_at)

    def test_release_rejects_invalid_minimum_and_duplicate_version(self):
        release = self.create_release(2)
        with self.assertRaises(HTTPException) as raised:
            update_app_release(
                release.id,
                AppReleaseUpdate(minimum_version_code=3),
                db=self.db,
                current_admin=self.admin,
            )
        self.assertEqual(raised.exception.status_code, 422)

        with self.assertRaises(HTTPException) as duplicate:
            self.create_release(2)
        self.assertEqual(duplicate.exception.status_code, 409)
