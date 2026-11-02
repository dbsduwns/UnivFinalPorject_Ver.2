from datetime import datetime, timedelta, timezone

from app.schemas.chat import ChatMessageResponse, MessengerSendResponse


def make_message(created_at: datetime) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=1,
        room_messenger_id=2,
        sender_id=3,
        content="hello",
        created_at=created_at,
    )


def test_naive_database_timestamp_is_returned_as_utc_for_message_list_and_send():
    message = make_message(datetime(2026, 11, 2, 6, 0))

    assert message.model_dump(mode="json")["created_at"] == "2026-11-02T06:00:00Z"
    assert MessengerSendResponse(message=message).model_dump(mode="json")["message"]["created_at"] == (
        "2026-11-02T06:00:00Z"
    )


def test_timezone_aware_timestamp_keeps_its_original_offset():
    kst = timezone(timedelta(hours=9))
    message = make_message(datetime(2026, 11, 2, 15, 0, tzinfo=kst))

    assert message.model_dump(mode="json")["created_at"] == "2026-11-02T15:00:00+09:00"
