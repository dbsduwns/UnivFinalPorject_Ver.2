from concurrent.futures import ThreadPoolExecutor
import json
import logging
from threading import Event
from unittest.mock import Mock

import pytest

from app.schemas.commute import RouteStopResponse, TransitLiveRequest
from app.services import transit_live as live
from app.services import transit_cache


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for key in ("PUBLIC_API_KEY", "SEOUL_BUS_API_KEY", "GYEONGGI_BUS_API_KEY", "TAGO_BUS_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for provider in ("SEOUL", "GYEONGGI", "TAGO"):
        monkeypatch.delenv(f"{provider}_BUS_DAILY_LIMIT", raising=False)
    live._cache.clear()
    live._usage.clear()
    live._cooldown.clear()
    monkeypatch.setattr(live.requests, "get", Mock(side_effect=AssertionError("Unexpected API call")))


def request(**updates):
    return TransitLiveRequest(**{
        "route_name": "5000", "vehicle_type": "BUS", "departure_stop_name": "기흥역",
        "arrival_stop_name": "강남대역", **updates,
    })


def gg_response(name, items, code=0):
    return Response({"response": {"msgHeader": {"resultCode": code}, "msgBody": {name: items}}})


def gg_api(monkeypatch, arrival=None):
    monkeypatch.setenv("GYEONGGI_BUS_API_KEY", "test")
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs["params"]))
        if "getBusRouteListv2" in url:
            return gg_response("busRouteList", {"routeId": 500, "routeName": "5000", "districtCd": 2})
        if "getBusRouteStationListv2" in url:
            return gg_response("busRouteStationList", [
                {"stationId": 10, "stationSeq": 10, "stationName": "이전정류장"},
                {"stationId": 11, "stationSeq": 11, "stationName": "기흥역"},
                {"stationId": 12, "stationSeq": 12, "stationName": "강남대역"},
            ])
        assert "getBusArrivalItemv2" in url  # No buslocationservice needed.
        assert kwargs["params"]["staOrder"] == 11
        return gg_response("busArrivalItem", arrival if arrival is not None else {
            "plateNo1": "경기1234", "predictTime1": 2, "predictTimeSec1": 61,
            "locationNo1": 1, "flag": "RUN",
        })

    monkeypatch.setattr(live.requests, "get", get)
    return calls


def test_gyeonggi_lazy_lookup_shares_cache_without_location_api(monkeypatch):
    calls = gg_api(monkeypatch)
    first = live.get_transit_live(request())
    second = live.get_transit_live(request())
    assert first.status == "ok"
    assert first.arrival_minutes == 2
    assert first.boarding_stop_order == 11
    assert first.alighting_stop_order == 12
    assert first.vehicles[0].current_stop_order == 10
    assert first.vehicles[0].latitude is None  # Stop position is not GPS.
    assert first.cached_at == second.cached_at
    assert len(calls) == 3


def test_live_cache_expires_but_static_mapping_survives(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(transit_cache, "monotonic", lambda: clock[0])
    calls = gg_api(monkeypatch)
    live.get_transit_live(request())
    clock[0] += 31
    live.get_transit_live(request())
    assert len(calls) == 4
    assert "getBusArrivalItemv2" in calls[-1][0]


def test_no_arrivals_back_off_and_preserve_stops(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(transit_cache, "monotonic", lambda: clock[0])
    calls = gg_api(monkeypatch, arrival={})
    result = live.get_transit_live(request())
    assert result.status == "no_data"
    assert result.arrival_minutes is None
    assert len(result.route_stops) == 3
    assert result.refresh_after_seconds == 120
    clock[0] += 31
    live.get_transit_live(request())
    assert len(calls) == 3


def test_seoul_message_and_vehicle_share_one_arrival_call(monkeypatch):
    monkeypatch.setenv("SEOUL_BUS_API_KEY", "test")
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if "getBusRouteList" in url:
            items = {"busRouteId": "100", "busRouteNm": "마포12"}
        elif "getStaionByRoute" in url:
            items = [{"seq": 10, "station": "a", "stationNm": "출발"},
                     {"seq": 11, "station": "b", "stationNm": "도착"}]
        else:
            assert "getArrInfoByRouteAll" in url
            items = {"stId": "a", "staOrd": 10, "arrmsg1": "3분18초후[1번째 전]",
                     "vehId1": "v1", "sectOrd1": "10"}
        return Response({"msgHeader": {"headerCd": "0"}, "msgBody": {"itemList": items}})

    monkeypatch.setattr(live.requests, "get", get)
    result = live.get_transit_live(request(route_name="마포 12", departure_stop_name="출발", arrival_stop_name="도착"))
    assert result.provider == "seoul"
    assert result.arrival_minutes == 4
    assert result.vehicle_number == "v1"
    assert len(calls) == 3


def test_missing_key_and_unsupported_modes_make_no_calls():
    assert live.get_transit_live(request()).status == "not_configured"
    assert live.get_transit_live(request(vehicle_type="SUBWAY")).status == "unsupported"
    live.requests.get.assert_not_called()


def test_api_error_is_not_empty_arrival_and_is_backed_off(monkeypatch, caplog):
    monkeypatch.setenv("SEOUL_BUS_API_KEY", "test")
    get = Mock(return_value=Response({"msgHeader": {"headerCd": "7"}, "msgBody": {}}))
    monkeypatch.setattr(live.requests, "get", get)
    with caplog.at_level(logging.WARNING, logger=live.__name__):
        first = live.get_transit_live(request(route_name="N62"))
    second = live.get_transit_live(request(route_name="N62"))
    assert first.status == second.status == "provider_error"
    assert get.call_count == 1
    provider_log = next(
        item.getMessage() for item in caplog.records
        if item.getMessage().startswith("Transit provider failed:")
    )
    assert "provider=seoul" in provider_log
    assert "reason=provider_result_error" in provider_log
    assert "result_code=7" in provider_log


def test_gateway_error_logs_safe_reason_code(monkeypatch, caplog):
    monkeypatch.setenv("PUBLIC_API_KEY", "secret-must-not-be-logged")
    get = Mock(return_value=Response({
        "cmmMsgHeader": {
            "returnReasonCode": "20",
            "errMsg": "SERVICE_ACCESS_DENIED_ERROR",
        }
    }))
    monkeypatch.setattr(live.requests, "get", get)
    with caplog.at_level(logging.WARNING, logger=live.__name__):
        result = live.get_transit_live(request(
            departure_stop_location={"latitude": 37.2, "longitude": 127.1},
        ))

    assert result.status == "provider_error"
    provider_log = next(
        item.getMessage() for item in caplog.records
        if item.getMessage().startswith("Transit provider failed:")
    )
    assert "provider=tago" in provider_log
    assert "operation=getCrdntPrxmtSttnList" in provider_log
    assert "reason=gateway_error" in provider_log
    assert "result_code=20" in provider_log
    assert "secret-must-not-be-logged" not in provider_log


def test_daily_budget_blocks_additional_upstream_calls(monkeypatch):
    monkeypatch.setenv("SEOUL_BUS_API_KEY", "test")
    monkeypatch.setenv("SEOUL_BUS_DAILY_LIMIT", "1")
    get = Mock(return_value=Response({"msgHeader": {"headerCd": "0"}, "msgBody": {"itemList": []}}))
    monkeypatch.setattr(live.requests, "get", get)
    live._request("seoul", "busRouteInfo", "getBusRouteList", {"strSrch": "N62"}, "itemList")
    with pytest.raises(live.ProviderError):
        live._request("seoul", "busRouteInfo", "getBusRouteList", {"strSrch": "N61"}, "itemList")
    assert get.call_count == 1


def test_match_requires_downstream_destination_and_rejects_distant_same_name():
    stops = [RouteStopResponse(stop_id="a", stop_name="기흥역", stop_order=1, latitude=37, longitude=127),
             RouteStopResponse(stop_id="b", stop_name="강남대역", stop_order=2)]
    assert live._match_segment(stops, request()) is not None
    assert live._match_segment(stops, request(departure_stop_name="강남대역", arrival_stop_name="기흥역")) is None
    assert live._match_segment(stops, request(departure_stop_location={"latitude": 38, "longitude": 127})) is None


def test_unmatched_log_distinguishes_direction_order(monkeypatch, caplog):
    gg_api(monkeypatch)
    with caplog.at_level(logging.WARNING, logger=live.__name__):
        result = live.get_transit_live(request(
            departure_stop_name="강남대역",
            arrival_stop_name="기흥역",
        ))

    assert result.status == "unmatched"
    record = next(
        item for item in caplog.records
        if "Transit route resolution failed:" in item.getMessage()
    )
    payload = json.loads(record.getMessage().split(": ", 1)[1])
    assert payload["event"] == "transit_route_unmatched"
    assert payload["reason"] == "providers_exhausted"
    assert "direction_order_mismatch" in payload["failure_reasons"]
    assert "api_key_not_configured" in payload["failure_reasons"]
    gyeonggi = payload["attempts"][0]
    assert gyeonggi["reason"] == "no_route_contains_requested_segment"
    assert gyeonggi["routes"][0]["reason"] == "direction_order_mismatch"
    assert gyeonggi["routes"][0]["departure_candidates"] == 1
    assert gyeonggi["routes"][0]["arrival_candidates"] == 1


def test_unmatched_log_reports_missing_provider_keys(monkeypatch, caplog):
    monkeypatch.setenv("PUBLIC_API_KEY", "test")
    get = Mock(return_value=Response({
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": {"item": []}},
        }
    }))
    monkeypatch.setattr(live.requests, "get", get)
    with caplog.at_level(logging.WARNING, logger=live.__name__):
        result = live.get_transit_live(request(
            agency_name="서울특별시",
            departure_stop_location={"latitude": 37.2, "longitude": 127.1},
        ))

    assert result.status == "unmatched"
    record = next(
        item for item in caplog.records
        if "Transit route resolution failed:" in item.getMessage()
    )
    payload = json.loads(record.getMessage().split(": ", 1)[1])
    assert payload["attempts"][0] == {
        "provider": "seoul",
        "reason": "api_key_not_configured",
    }
    assert payload["attempts"][1] == {
        "provider": "gyeonggi",
        "reason": "api_key_not_configured",
    }
    assert payload["attempts"][2]["provider"] == "tago"


def test_cache_singleflight_and_copies():
    cache = transit_cache.RequestCache()
    entered, release, follower_entered = Event(), Event(), Event()
    calls = []

    def load():
        calls.append(1)
        entered.set()
        assert release.wait(2)
        return ["value"]

    def follow():
        follower_entered.set()
        return cache.get("key", load)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get, "key", load)
        assert entered.wait(2)
        second = pool.submit(follow)
        assert follower_entered.wait(2)
        release.set()
        a, b = first.result(), second.result()
    a.append("mutated")
    assert b == ["value"]
    assert len(calls) == 1


def test_xml_and_empty_response_shapes(monkeypatch):
    monkeypatch.setenv("GYEONGGI_BUS_API_KEY", "test")
    xml_response = Mock()
    xml_response.json.side_effect = ValueError("XML")
    xml_response.content = b"<response><msgHeader><resultCode>0</resultCode></msgHeader><msgBody><busRouteList><routeId>1</routeId></busRouteList><busRouteList><routeId>2</routeId></busRouteList></msgBody></response>"
    get = Mock(return_value=xml_response)
    monkeypatch.setattr(live.requests, "get", get)
    items = live._request("gyeonggi", "busrouteservice", "getBusRouteList", {"keyword": "1"}, "busRouteList")
    assert [item["routeId"] for item in items] == ["1", "2"]
    get.return_value = gg_response("busRouteList", {}, code=4)
    assert live._request("gyeonggi", "busrouteservice", "getBusRouteList", {"keyword": "2"}, "busRouteList") == []


@pytest.mark.parametrize("positions_fail", [False, True])
def test_tago_fallback_and_location_failure_preserves_arrival(monkeypatch, positions_fail):
    monkeypatch.setenv("PUBLIC_API_KEY", "test")
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if "getCrdntPrxmtSttnList" in url:
            items = {"citycode": "23"}
        elif "getRouteNoList" in url:
            items = {"routeid": "R", "routeno": "5000"}
        elif "getRouteAcctoThrghSttnList" in url:
            items = [{"nodeord": 1, "nodeid": "a", "nodenm": "기흥역"},
                     {"nodeord": 2, "nodeid": "b", "nodenm": "강남대역"}]
        elif "getSttnAcctoArvlPrearngeInfoList" in url:
            items = {"routeid": "R", "arrtime": 100}
        else:
            assert "getRouteAcctoBusLcList" in url
            if positions_fail:
                raise live.requests.Timeout()
            items = {"nodeord": 1, "vehicleno": "BUS1"}
        return Response({"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": items}}}})

    monkeypatch.setattr(live.requests, "get", get)
    query = request(departure_stop_location={"latitude": 37.2, "longitude": 127.1})
    result = live.get_transit_live(query)
    assert result.status == "ok"
    assert result.provider == "tago"
    assert result.arrival_minutes == 2
    assert len(result.vehicles) == (0 if positions_fail else 1)
    live.get_transit_live(query)
    assert len(calls) == 5
