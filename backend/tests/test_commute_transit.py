from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services import commute


class FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


def tago_response(items: list[dict] | dict) -> dict:
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "OK"},
            "body": {"items": {"item": items}},
        }
    }


def test_resolve_tago_stop_selects_nearest_same_name(monkeypatch):
    monkeypatch.setattr(commute, "PUBLIC_API_KEY", "test-key")
    candidates = [
        {
            "nodeid": "FAR_STOP",
            "citycode": "31190",
            "nodenm": "기흥역 정류장",
            "gpslati": "37.276000",
            "gpslong": "127.116000",
        },
        {
            "nodeid": "NEAR_STOP",
            "citycode": "31190",
            "nodenm": "기흥역",
            "gpslati": "37.275050",
            "gpslong": "127.115050",
        },
    ]
    monkeypatch.setattr(
        commute.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(tago_response(candidates)),
    )

    result = commute.resolve_tago_stop(
        latitude=37.275000,
        longitude=127.115000,
        stop_name="기흥역",
    )

    assert result is not None
    assert result["node_id"] == "NEAR_STOP"
    assert result["city_code"] == "31190"


def test_get_transit_route_adds_matching_tago_arrival(monkeypatch):
    monkeypatch.setattr(commute, "GOOGLE_MAPS_SERVER_API_KEY", "google-key")
    monkeypatch.setattr(commute, "PUBLIC_API_KEY", "public-key")

    google_data = {
        "routes": [
            {
                "duration": "1800s",
                "distanceMeters": 12000,
                "polyline": {
                    "geoJsonLinestring": {
                        "coordinates": [
                            [127.1, 37.2],
                            [127.15, 37.25],
                            [127.2, 37.3],
                        ]
                    }
                },
                "legs": [
                    {
                        "steps": [
                            {
                                "travelMode": "WALK",
                                "staticDuration": "300s",
                                "distanceMeters": 450,
                                "navigationInstruction": {
                                    "instructions": "기흥역까지 걷기"
                                },
                                "polyline": {
                                    "geoJsonLinestring": {
                                        "coordinates": [
                                            [127.1, 37.2],
                                            [127.11, 37.21],
                                        ]
                                    }
                                },
                            },
                            {
                                "travelMode": "TRANSIT",
                                "staticDuration": "1200s",
                                "distanceMeters": 10500,
                                "polyline": {
                                    "geoJsonLinestring": {
                                        "coordinates": [
                                            [127.11, 37.21],
                                            [127.19, 37.29],
                                        ]
                                    }
                                },
                                "transitDetails": {
                                    "stopDetails": {
                                        "departureStop": {
                                            "name": "기흥역",
                                            "location": {
                                                "latLng": {
                                                    "latitude": 37.275,
                                                    "longitude": 127.115,
                                                }
                                            },
                                        },
                                        "arrivalStop": {"name": "강남대역"},
                                    },
                                    "transitLine": {
                                        "nameShort": "5000",
                                        "name": "직행좌석 5000",
                                        "vehicle": {"type": "BUS"},
                                    },
                                },
                            },
                            {
                                "travelMode": "WALK",
                                "staticDuration": "300s",
                                "distanceMeters": 350,
                                "polyline": {
                                    "geoJsonLinestring": {
                                        "coordinates": [
                                            [127.19, 37.29],
                                            [127.2, 37.3],
                                        ]
                                    }
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    google_request = {}

    def fake_post(url, **kwargs):
        google_request["url"] = url
        google_request.update(kwargs)
        return FakeResponse(google_data)

    monkeypatch.setattr(commute.requests, "post", fake_post)

    def fake_get(url, **kwargs):
        if url == commute.TAGO_STOP_API_URL:
            return FakeResponse(
                tago_response(
                    {
                        "nodeid": "GGB123",
                        "citycode": "31190",
                        "nodenm": "기흥역",
                        "gpslati": "37.275010",
                        "gpslong": "127.115010",
                    }
                )
            )
        assert url == commute.TAGO_ARRIVAL_API_URL
        return FakeResponse(
            tago_response(
                [
                    {
                        "routeid": "GGB_OTHER",
                        "routeno": "5005",
                        "arrtime": "120",
                        "arrprevstationcnt": "1",
                    },
                    {
                        "routeid": "GGB_5000",
                        "routeno": "5000",
                        "arrtime": "481",
                        "arrprevstationcnt": "4",
                    },
                ]
            )
        )

    monkeypatch.setattr(commute.requests, "get", fake_get)

    result = commute.get_transit_route(
        start_latitude=37.2,
        start_longitude=127.1,
        end_latitude=37.3,
        end_longitude=127.2,
        arrival_time=datetime(
            2026,
            10,
            19,
            9,
            0,
            tzinfo=ZoneInfo("Asia/Seoul"),
        ),
    )

    assert google_request["url"] == commute.GOOGLE_ROUTES_API_URL
    assert google_request["json"]["travelMode"] == "TRANSIT"
    assert google_request["json"]["computeAlternativeRoutes"] is False
    assert "routingPreference" not in google_request["json"]
    assert google_request["json"]["arrivalTime"] == "2026-10-19T00:00:00Z"
    assert google_request["headers"]["X-Goog-FieldMask"] == (
        commute.GOOGLE_ROUTES_FIELD_MASK
    )
    assert result.transport_type == "bus"
    assert result.route_name == "5000"
    assert result.duration_minutes == 30
    assert result.walking_minutes == 10
    assert result.transfer_count == 0
    assert result.boarding_stop_name == "기흥역"
    assert result.bus_arrival_minutes == 9
    assert result.bus_remaining_stops == 4
    assert "5000번 버스" in result.recommendation_reason
    assert result.route_path[0].latitude == 37.2
    assert result.route_path[0].longitude == 127.1
    assert len(result.route_steps) == 3
    assert result.route_steps[0].travel_mode == "WALK"
    assert result.route_steps[0].instruction == "기흥역까지 걷기"
    assert result.route_steps[1].transit_line_name == "5000"
    assert result.route_steps[1].departure_stop_name == "기흥역"
    assert result.route_steps[1].route_path[-1].longitude == 127.19


def test_get_today_commute_returns_campus_travel_time_without_class(monkeypatch):
    profile = SimpleNamespace(
        home_latitude=37.2,
        home_longitude=127.1,
        use_shuttle=True,
        departure_buffer_minutes=10,
    )
    route = commute.RouteSummaryResponse(
        transport_type="bus",
        route_name="5000",
        duration_minutes=35,
        walking_minutes=7,
        transfer_count=0,
        is_recommended=True,
    )
    route_request = {}

    monkeypatch.setattr(commute, "get_commute_profile", lambda db, user: profile)
    monkeypatch.setattr(commute, "get_first_class", lambda db, user: None)

    def fake_get_transit_route(**kwargs):
        route_request.update(kwargs)
        return route

    monkeypatch.setattr(commute, "get_transit_route", fake_get_transit_route)

    result = commute.get_today_commute(db=object(), user=object())

    assert result.status == "ready"
    assert result.display_mode == "travel_time_only"
    assert result.message == "오늘 예정된 정규 수업이 없습니다."
    assert result.first_class is None
    assert result.destination is not None
    assert result.destination.destination_type == "campus_gate"
    assert result.destination.destination_name == "강남대학교"
    assert result.recommended_route is route
    assert result.recommended_route.duration_minutes == 35
    assert route_request["end_latitude"] == commute.CAMPUS_DEFAULT_LATITUDE
    assert route_request["end_longitude"] == commute.CAMPUS_DEFAULT_LONGITUDE
    assert route_request["arrival_time"] is None
    assert route_request["departure_time"].tzinfo is not None
