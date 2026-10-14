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
    monkeypatch.setattr(commute, "TMAP_API_KEY", "tmap-key")
    monkeypatch.setattr(commute, "PUBLIC_API_KEY", "public-key")

    tmap_data = {
        "metaData": {
            "plan": {
                "itineraries": [
                    {
                        "totalTime": 1800,
                        "totalWalkTime": 300,
                        "transferCount": 0,
                        "legs": [
                            {"mode": "WALK", "sectionTime": 300},
                            {
                                "mode": "BUS",
                                "route": "직행좌석:5000",
                                "passStopList": {
                                    "stationList": [
                                        {
                                            "stationName": "기흥역",
                                            "lat": "37.275000",
                                            "lon": "127.115000",
                                            "stationID": "TMAP123",
                                        }
                                    ]
                                },
                            },
                        ],
                    }
                ]
            }
        }
    }
    monkeypatch.setattr(
        commute.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(tmap_data),
    )

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
    )

    assert result.boarding_stop_name == "기흥역"
    assert result.bus_arrival_minutes == 9
    assert result.bus_remaining_stops == 4
    assert "5000번 버스" in result.recommendation_reason
