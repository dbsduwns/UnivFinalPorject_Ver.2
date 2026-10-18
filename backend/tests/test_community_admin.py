import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.community import Post, Comment, CommentReport, UserBlock, PostLike, CommentLike
from app.routers.admin import router
from app.routers.community.comment_report import admin_router
from app.routers.community.comment_report import router as report_router
from app.routers.community.post import router as post_router, admin_router as post_admin_router
from app.routers.community.comment import router as comment_router, admin_router as comment_admin_router


class CommunityAdminTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        for model in (User, Post, Comment, CommentReport, UserBlock, PostLike, CommentLike):
            model.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.user = SimpleNamespace(id=1, is_admin=True)
        self.db.add_all([User(id=i, email=f"user{i}@test.com", name=f"User {i}", password_hash="test") for i in range(1, 4)])
        self.db.add_all([UserBlock(blocker_id=2, blocked_user_id=3), UserBlock(blocker_id=3, blocked_user_id=2)])
        self.db.add(CommentReport(reporter_id=2, reported_user_id=3, reason="spam", content_snapshot="신고된 댓글"))
        self.db.commit()
        app = FastAPI()
        app.include_router(router)
        app.include_router(admin_router)
        for additional_router in (report_router, post_router, post_admin_router, comment_router, comment_admin_router):
            app.include_router(additional_router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_admin_sees_all_blocks_and_pagination(self):
        response = self.client.get("/api/admin/user-blocks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual({item["blocker_id"] for item in response.json()}, {2, 3})
        self.assertEqual(len(self.client.get("/api/admin/user-blocks?skip=1&limit=1").json()), 1)
        self.assertEqual(self.client.get("/api/admin/user-blocks?limit=101").status_code, 422)

    def test_report_review_requires_note_and_records_admin(self):
        report = self.client.get("/api/admin/comment-reports").json()[0]
        self.assertEqual(report["content_snapshot"], "신고된 댓글")
        path = f'/api/admin/comment-reports/{report["id"]}'
        self.assertEqual(self.client.patch(path, json={"status": "resolved"}).status_code, 422)
        response = self.client.patch(path, json={"status": "resolved", "resolution_note": "검토 완료"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reviewed_by_id"], 1)
        self.assertEqual(response.json()["status"], "resolved")
        self.assertIsNotNone(response.json()["reviewed_at"])

    def test_regular_user_cannot_read_or_review(self):
        self.user.is_admin = False
        self.assertEqual(self.client.get("/api/admin/user-blocks").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/comment-reports").status_code, 403)
        self.assertEqual(self.client.patch("/api/admin/comment-reports/1", json={"status": "reviewing"}).status_code, 403)

    def test_post_moderation_for_every_board_and_public_visibility(self):
        for board in ("free", "freshman", "graduate", "market", "club", "career"):
            self.user.id = 2
            self.user.is_admin = False
            created = self.client.post(f"/api/community/posts?board_slug={board}", json={"title": "원본", "content": "본문"}).json()
            recent = self.client.post(f"/api/community/posts?board_slug={board}", json={"title": "최신", "content": "본문"}).json()
            slug = created["slug"]
            path = f"/api/admin/community/posts/{slug}"
            self.assertEqual(self.client.patch(path, json={"is_pinned": True}).status_code, 403)
            self.user.id, self.user.is_admin = 1, True
            updated = self.client.patch(path, json={"title": "관리자 수정", "content": "수정 본문", "is_pinned": True})
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()["title"], "관리자 수정")
            self.assertEqual(self.client.get(f"/api/community/?board_slug={board}").json()[0]["id"], created["id"])
            self.client.patch(path, json={"is_pinned": False})
            self.assertEqual(self.client.get(f"/api/community/?board_slug={board}").json()[0]["id"], recent["id"])
            self.client.patch(path, json={"is_hidden": True})
            self.assertEqual(self.client.get("/api/community/slug", params={"post_slug": slug}).status_code, 404)
            self.assertNotIn(created["id"], [item["id"] for item in self.client.get(f"/api/community/?board_slug={board}").json()])
            self.assertEqual(len(self.client.get(f"/api/admin/community/posts?board_slug={board}").json()), 2)
            self.assertEqual(self.client.get(path).status_code, 200)
            self.client.patch(path, json={"is_hidden": False})
            self.assertEqual(self.client.get("/api/community/slug", params={"post_slug": slug}).status_code, 200)
            self.assertEqual(self.client.delete(f"/api/community/{slug}").status_code, 200)

    def test_report_counts_my_status_and_comment_moderation(self):
        self.db.add(Post(id=10, slug="reported-post", board_slug="free", title="글", content="내용", author_id=2))
        self.db.commit()
        self.db.add(Comment(id=10, post_id=10, author_id=3, content="신고 원문"))
        self.db.commit()
        self.db.add_all([CommentReport(reporter_id=reporter, reported_user_id=3, comment_id=10, reason="spam", content_snapshot="신고 원문") for reporter in (1, 2)])
        self.db.commit()
        records = self.client.get("/api/admin/comment-reports").json()
        record = next(item for item in records if item["comment_id"] == 10)
        self.assertEqual(record["report_count"], 2)
        self.assertEqual(record["pending_report_count"], 2)
        self.assertEqual(record["post_id"], 10)
        report_path = f'/api/admin/comment-reports/{record["id"]}'
        self.client.patch(report_path, json={"status": "resolved", "resolution_note": "관리자 메모"})
        self.assertEqual(self.client.get(report_path).json()["pending_report_count"], 1)
        moderation = "/api/admin/community/comments/10/10/moderation"
        self.assertEqual(self.client.patch(moderation, json={"action": "hide", "reason": "누적 신고"}).status_code, 200)
        self.assertTrue(self.client.get(report_path).json()["comment_is_hidden"])
        self.user.id, self.user.is_admin = record["reporter_id"], False
        own = self.client.get("/api/community/my-comment-reports").json()
        self.assertEqual({item["id"] for item in own}, {row.id for row in self.db.query(CommentReport).filter(CommentReport.reporter_id == self.user.id).all()})
        own_record = next(item for item in own if item["id"] == record["id"])
        self.assertEqual(own_record["status"], "resolved")
        self.assertNotIn("resolution_note", own_record)
        self.assertNotIn("reporter_id", own_record)
        self.assertEqual(self.client.patch(moderation, json={"action": "restore"}).status_code, 403)
        self.assertNotEqual(self.client.get("/api/community/comments/10/10").json()["content"], "신고 원문")
        self.user.id, self.user.is_admin = 1, True
        self.client.patch(moderation, json={"action": "restore"})
        self.assertFalse(self.client.get(report_path).json()["comment_is_hidden"])
        self.assertEqual(self.client.delete("/api/community/comments/10/10").status_code, 200)
        after = self.client.get(report_path).json()
        self.assertIsNone(after["comment_id"])
        self.assertEqual(after["content_snapshot"], "신고 원문")

    def test_post_delete_preserves_report_snapshots(self):
        self.db.add(Post(id=10, slug="delete-post", board_slug="free", title="글", content="내용", author_id=2))
        self.db.commit()
        self.db.add(Comment(id=10, post_id=10, author_id=3, content="원문"))
        self.db.commit()
        self.db.add_all([CommentReport(reporter_id=2, reported_user_id=3, comment_id=10, reason="spam", content_snapshot="원문"), PostLike(user_id=2, post_id=10), CommentLike(user_id=2, comment_id=10)])
        self.db.commit()
        self.assertEqual(self.client.delete("/api/community/delete-post").status_code, 200)
        self.assertIsNone(self.db.get(Comment, 10))
        self.assertEqual(self.db.query(PostLike).count(), 0)
        self.assertEqual(self.db.query(CommentLike).count(), 0)
        report = self.db.query(CommentReport).filter(CommentReport.content_snapshot == "원문").one()
        self.assertIsNone(report.comment_id)

    def test_new_post_fields_migration(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from sqlalchemy import text

        source = Path(__file__).resolve().parents[1] / "alembic/versions/a8b9c0d1e2f3_add_community_post_moderation.py"
        spec = importlib.util.spec_from_file_location("post_moderation_migration", source)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE posts (id INTEGER PRIMARY KEY)"))
                connection.execute(text("INSERT INTO posts (id) VALUES (1)"))
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                    self.assertEqual(tuple(connection.execute(text("SELECT is_hidden, is_pinned FROM posts")).one()), (0, 0))
                    migration.downgrade()
                self.assertEqual(connection.execute(text("SELECT id FROM posts")).scalar(), 1)
        finally:
            engine.dispose()
