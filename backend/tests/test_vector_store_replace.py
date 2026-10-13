from types import SimpleNamespace

from app.core.vector_store import QdrantDocumentStore


class FakeQdrantClient:
    def __init__(self, pages):
        self.pages = pages
        self.deleted = None
        self.scroll_calls = []

    def scroll(self, **kwargs):
        self.scroll_calls.append(kwargs)
        page_index = 0 if kwargs.get("offset") is None else 1
        return self.pages[page_index]

    def delete(self, **kwargs):
        self.deleted = kwargs


def _record(point_id, source):
    return SimpleNamespace(
        id=point_id,
        payload={"metadata": {"source": source}},
    )


def test_replace_documents_filters_source_client_side_and_deletes_only_stale_points():
    store = QdrantDocumentStore.__new__(QdrantDocumentStore)
    store.collection_name = "test-collection"
    current_id = store._point_id("current")
    stale_id = store._point_id("stale")
    unrelated_id = store._point_id("notice")
    store.client = FakeQdrantClient(
        [
            ([_record(stale_id, "학사일정"), _record(unrelated_id, "공지사항")], "next"),
            ([_record(current_id, "학사일정")], None),
        ]
    )
    store.add_documents = lambda documents, ids=None: None

    removed = store.replace_documents_by_source(
        [SimpleNamespace()],
        ids=["current"],
        source="학사일정",
    )

    assert removed == 1
    assert len(store.client.scroll_calls) == 2
    assert all("scroll_filter" not in call for call in store.client.scroll_calls)
    assert store.client.deleted["points_selector"].points == [stale_id]
