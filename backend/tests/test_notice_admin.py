import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.notice import Notice
from app.models.notice_read import NoticeRead
from app.models.user import User
from app.routers.notice import router


class NoticeAdminTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, Notice.__table__, NoticeRead.__table__):
            table.create(self.engine)
        self.db = Session(self.engine)
        self.user = SimpleNamespace(is_admin=True)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def create(self, title="공지"):
        response = self.client.post("/api/notices/", json={"title": title, "content": "본문", "category": "학사"})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_create_edit_pin_unpin_and_delete(self):
        first = self.create("이전 공지")
        second = self.create("새 공지")
        response = self.client.put(f"/api/notices/{first}", json={"is_important": True, "title": "수정 공지", "content": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], "")
        self.assertEqual(response.json()["title"], "수정 공지")
        self.assertEqual(self.client.get("/api/notices/").json()[0]["id"], first)
        self.client.put(f"/api/notices/{first}", json={"is_important": False})
        self.assertEqual(self.client.get("/api/notices/").json()[0]["id"], second)
        self.assertEqual(self.client.delete(f"/api/notices/{first}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/notices/{first}").status_code, 404)

    def test_regular_user_cannot_manage_notices(self):
        notice_id = self.create()
        self.user.is_admin = False
        self.assertEqual(self.client.post("/api/notices/", json={"title": "공지", "content": "본문", "category": "학사"}).status_code, 403)
        self.assertEqual(self.client.put(f"/api/notices/{notice_id}", json={"is_important": True}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/notices/{notice_id}").status_code, 403)
        self.assertEqual(self.client.get("/api/notices/").status_code, 200)

    def test_invalid_and_missing_notice(self):
        self.assertEqual(self.client.post("/api/notices/", json={"title": "", "content": "본문", "category": "학사"}).status_code, 422)
        self.assertEqual(self.client.put("/api/notices/999", json={"is_important": True}).status_code, 404)
        self.assertEqual(self.client.delete("/api/notices/999").status_code, 404)

    def test_public_title_search_keeps_pinned_first_and_filters_category(self):
        pinned = self.create("장학 신청 안내")
        recent = self.create("장학 신청 마감")
        self.create("수강 안내")
        self.client.put(f"/api/notices/{pinned}", json={"is_important": True, "category": "장학"})
        self.user.is_admin = False
        results = self.client.get("/api/notices/", params={"keyword": " 장학 "})
        self.assertEqual(results.status_code, 200)
        self.assertEqual([item["id"] for item in results.json()], [pinned, recent])
        self.assertEqual([item["id"] for item in self.client.get("/api/notices/", params={"keyword": "장학", "category": "장학"}).json()], [pinned])
        self.assertEqual(self.client.get("/api/notices/", params={"keyword": "없는검색어"}).json(), [])
        self.assertEqual(len(self.client.get("/api/notices/", params={"keyword": "   "}).json()), 3)

    def test_search_treats_wildcards_as_text(self):
        matching = self.create("등록금 50% 안내")
        self.create("일반 안내")
        self.assertEqual([item["id"] for item in self.client.get("/api/notices/", params={"keyword": "%"}).json()], [matching])
