"""Lazy public-transit enrichment. Never called by the route prediction service.

Static route matching is cached for six hours; real-time reads are shared for
30 seconds, empty responses for two minutes, and failures for one minute.
Seoul/GBIS arrival responses already identify the approaching vehicle's stop,
so the stop-list UI does not need an additional vehicle-location request.
"""

from datetime import datetime, timezone
import json
import logging
import math
import os
import re
from threading import Lock
from time import monotonic
from urllib.parse import unquote
from zoneinfo import ZoneInfo
from xml.etree import ElementTree

import requests

from app.schemas.commute import (
    LiveBusPositionResponse, RouteStopResponse, TransitLiveRequest, TransitLiveResponse,
)
from app.services.transit_cache import RequestCache

logger = logging.getLogger(__name__)
STATIC_TTL = 6 * 3600
LIVE_TTL = 30
EMPTY_TTL = 120
FAILURE_TTL = 60
# 서울 버스 api URL
SEOUL_BUS_API_BASE_URL = "http://ws.bus.go.kr/api/rest"
_cache = RequestCache(1024)
_policy_lock = Lock()
_cooldown = {}
_usage = {}


class ProviderError(Exception):
    def __init__(self, message, *, reason="provider_error", result_code=None):
        super().__init__(message)
        self.reason = reason
        self.result_code = result_code


def _key(provider):
    # New APIs require separate activation even if the portal uses the same key.
    # Explicit opt-in avoids repeatedly trying APIs not enabled for the account.
    return os.getenv(f"{provider.upper()}_BUS_API_KEY") or (
        os.getenv("PUBLIC_API_KEY") if provider == "tago" else None
    )


def _list(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return [value] if isinstance(value, dict) else []


def _text(value):
    return str(value if value is not None else "").strip()


def _number(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _name(value):
    return re.sub(r"[\s.·ㆍ()（）]", "", _text(value)).lower()


def _route_name(value):
    return re.sub(r"(?:번|버스)$", "", _name(value)).upper()


def _xml_value(node):
    if not len(node):
        return node.text or ""
    result = {}
    for child in node:
        value = _xml_value(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return result


def _request(provider, service, operation, params, item_key, static=False):
    """Cache the provider operation, allowing different users/segments to share it."""
    cache_key = (provider, service, operation, tuple(sorted(params.items())))

    def load():
        api_key = _key(provider)
        if not api_key:
            raise ProviderError("실시간 API 키가 설정되지 않았습니다.")
        # Authentication/quota failures must not trigger a fresh call for each stop.
        with _policy_lock:
            if _cooldown.get((provider, service), 0) > monotonic():
                raise ProviderError("실시간 제공기관에 잠시 연결할 수 없습니다.")
            today = datetime.now(ZoneInfo("Asia/Seoul")).date()
            default_limit = 9000 if provider == "tago" else 900
            try:
                limit = max(0, int(os.getenv(f"{provider.upper()}_BUS_DAILY_LIMIT", str(default_limit))))
            except ValueError:
                limit = default_limit
            budget_key = (provider, service)
            usage_day, count = _usage.get(budget_key, (today, 0))
            if usage_day != today:
                count = 0
            if count >= limit:
                raise ProviderError("오늘의 실시간 조회 한도에 도달했습니다.")
            _usage[budget_key] = (today, count + 1)
        query = {"serviceKey": unquote(api_key), **params}
        if provider == "seoul":
            url = f"{SEOUL_BUS_API_BASE_URL}/{service}/{operation}"
            query["resultType"] = "json"
        elif provider == "gyeonggi":
            url = f"https://apis.data.go.kr/6410000/{service}/v2/{operation}v2"
            query["format"] = "json"
        else:
            url = f"https://apis.data.go.kr/1613000/{service}/{operation}"
            query.update(_type="json", numOfRows=300, pageNo=1)
        try:
            response = requests.get(url, params=query, timeout=(2, 5))
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                data = _xml_value(ElementTree.fromstring(response.content))
            if not isinstance(data, dict):
                raise ProviderError(
                    "실시간 응답 형식을 확인할 수 없습니다.",
                    reason="invalid_payload",
                )
            if "cmmMsgHeader" in data:
                gateway_header = data.get("cmmMsgHeader") or {}
                raise ProviderError(
                    "공공 API 인증 또는 호출 한도를 확인해주세요.",
                    reason="gateway_error",
                    result_code=_text(
                        gateway_header.get("returnReasonCode")
                        if isinstance(gateway_header, dict)
                        else None
                    ) or None,
                )
            if provider == "tago":
                envelope = data.get("response", data)
                code = _text((envelope.get("header") or {}).get("resultCode"))
                body = envelope.get("body") or {}
                items = (body.get("items") or {}).get("item") if isinstance(body.get("items"), dict) else None
                ok, empty = {"00", "0"}, {"03"}
            else:
                envelope = data.get("response", data)
                header = envelope.get("msgHeader") or {}
                code = _text(header.get("headerCd") if provider == "seoul" else header.get("resultCode"))
                body = envelope.get("msgBody") or {}
                items = body.get(item_key) if isinstance(body, dict) else None
                ok, empty = {"0", "00"}, {"4"}
            if code in empty:
                return []
            if code not in ok:
                raise ProviderError(
                    "실시간 API 응답 오류입니다.",
                    reason="provider_result_error",
                    result_code=code or None,
                )
            fetched_at = datetime.now(timezone.utc).isoformat()
            return [{**item, "_fetched_at": fetched_at} for item in _list(items)]
        except (requests.RequestException, ValueError, ElementTree.ParseError, ProviderError, TypeError, AttributeError) as exc:
            with _policy_lock:
                _cooldown[(provider, service)] = monotonic() + FAILURE_TTL
            # URLs/exceptions can contain credentials. Log only safe classifications.
            if isinstance(exc, requests.Timeout):
                reason, result_code = "timeout", None
            elif isinstance(exc, requests.HTTPError):
                reason, result_code = "http_error", None
            elif isinstance(exc, requests.RequestException):
                reason, result_code = "network_error", None
            elif isinstance(exc, ElementTree.ParseError):
                reason, result_code = "xml_parse_error", None
            elif isinstance(exc, ProviderError):
                reason, result_code = exc.reason, exc.result_code
            else:
                reason, result_code = "response_parse_error", None
            status_code = (
                exc.response.status_code
                if isinstance(exc, requests.HTTPError) and exc.response is not None
                else None
            )
            logger.warning(
                "Transit provider failed: provider=%s service=%s operation=%s "
                "reason=%s http_status=%s result_code=%s",
                provider,
                service,
                operation,
                reason,
                status_code,
                result_code,
            )
            raise ProviderError("실시간 정보를 일시적으로 조회하지 못했습니다.") from exc

    return _cache.get(cache_key, load, ttl=STATIC_TTL if static else LIVE_TTL,
                      empty_ttl=EMPTY_TTL, error_ttl=FAILURE_TTL)


def _stops(provider, route_id, city_code=""):
    if provider == "seoul":
        items = _request(provider, "busRouteInfo", "getStaionByRoute",
                         {"busRouteId": route_id}, "itemList", static=True)
        fields = ("seq", "station", "stationNm", "gpsY", "gpsX")
    elif provider == "gyeonggi":
        items = _request(provider, "busrouteservice", "getBusRouteStationList",
                         {"routeId": route_id}, "busRouteStationList", static=True)
        fields = ("stationSeq", "stationId", "stationName", "y", "x")
    else:
        items = _request(provider, "BusRouteInfoInqireService", "getRouteAcctoThrghSttnList",
                         {"cityCode": city_code, "routeId": route_id}, "item", static=True)
        fields = ("nodeord", "nodeid", "nodenm", "gpslati", "gpslong")
    stops = []
    for item in items:
        order = _number(item.get(fields[0]))
        stop_id, name = _text(item.get(fields[1])), _text(item.get(fields[2]))
        if order is None or order < 0 or not stop_id or not name:
            continue
        try:
            lat, lng = float(item[fields[3]]), float(item[fields[4]])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                lat, lng = None, None
        except (TypeError, ValueError, KeyError):
            lat, lng = None, None
        stops.append(RouteStopResponse(stop_order=order, stop_id=stop_id,
                                       stop_name=name, latitude=lat, longitude=lng))
    return sorted(stops, key=lambda stop: stop.stop_order)


def _stop_score(stop, name, location):
    name_matches = _name(stop.stop_name) == _name(name)
    distance = None
    if location and stop.latitude is not None and stop.longitude is not None:
        # Local-distance approximation, sufficient for a <=200m matching gate.
        dy = (location.latitude - stop.latitude) * 111_000
        dx = (location.longitude - stop.longitude) * 111_000 * math.cos(math.radians(location.latitude))
        distance = math.hypot(dx, dy)
        if distance > 200:
            return None
    if not name_matches and (distance is None or distance > 50):
        return None
    return (0 if name_matches else 500) + (distance or 0)


def _distance_to_stop(stop, location):
    if not location or stop.latitude is None or stop.longitude is None:
        return None
    dy = (location.latitude - stop.latitude) * 111_000
    dx = (
        (location.longitude - stop.longitude)
        * 111_000
        * math.cos(math.radians(location.latitude))
    )
    return math.hypot(dx, dy)


def _same_name_distance(stops, name, location):
    distances = [
        _distance_to_stop(stop, location)
        for stop in stops
        if _name(stop.stop_name) == _name(name)
    ]
    usable = [distance for distance in distances if distance is not None]
    return round(min(usable), 1) if usable else None


def _match_segment_diagnostic(stops, request):
    """Return a direction-safe segment and a non-sensitive matching diagnostic."""
    matches = []
    starts = []
    arrivals = []
    for start in stops:
        score = _stop_score(start, request.departure_stop_name, request.departure_stop_location)
        if score is None:
            continue
        starts.append(start)
        for end in stops:
            end_score = _stop_score(end, request.arrival_stop_name, request.arrival_stop_location)
            if end_score is not None and end not in arrivals:
                arrivals.append(end)
            if end.stop_order <= start.stop_order:
                continue
            if end_score is not None:
                matches.append((score + end_score, end.stop_order - start.stop_order, start, end))
    details = {
        "stop_count": len(stops),
        "departure_name_matches": sum(
            _name(stop.stop_name) == _name(request.departure_stop_name) for stop in stops
        ),
        "arrival_name_matches": sum(
            _name(stop.stop_name) == _name(request.arrival_stop_name) for stop in stops
        ),
        "departure_candidates": len(starts),
        "arrival_candidates": len(arrivals),
        "departure_same_name_distance_m": _same_name_distance(
            stops, request.departure_stop_name, request.departure_stop_location
        ),
        "arrival_same_name_distance_m": _same_name_distance(
            stops, request.arrival_stop_name, request.arrival_stop_location
        ),
    }
    if not starts:
        details["reason"] = (
            "departure_coordinate_mismatch"
            if details["departure_name_matches"] > 0
            and details["departure_same_name_distance_m"] is not None
            and details["departure_same_name_distance_m"] > 200
            else "departure_stop_not_found"
        )
        return None, details
    if not arrivals:
        details["reason"] = (
            "arrival_coordinate_mismatch"
            if details["arrival_name_matches"] > 0
            and details["arrival_same_name_distance_m"] is not None
            and details["arrival_same_name_distance_m"] > 200
            else "arrival_stop_not_found"
        )
        return None, details
    if not matches:
        details["reason"] = "direction_order_mismatch"
        return None, details
    matches.sort(key=lambda match: (match[0], match[1]))
    # Same-name/coordinate stops can exist in both directions on a loop. Refuse ties.
    if len(matches) > 1 and matches[0][:2] == matches[1][:2]:
        details["reason"] = "ambiguous_stop_pair"
        details["segment_matches"] = len(matches)
        return None, details
    details["reason"] = "matched"
    details["boarding_order"] = matches[0][2].stop_order
    details["alighting_order"] = matches[0][3].stop_order
    details["boarding_stop_id"] = matches[0][2].stop_id
    details["boarding_stop_name"] = matches[0][2].stop_name
    details["alighting_stop_id"] = matches[0][3].stop_id
    details["alighting_stop_name"] = matches[0][3].stop_name
    details["boarding_match_distance_m"] = _distance_to_stop(
        matches[0][2], request.departure_stop_location
    )
    details["alighting_match_distance_m"] = _distance_to_stop(
        matches[0][3], request.arrival_stop_location
    )
    return matches[0][2:], details


def _match_segment(stops, request):
    """Require boarding and downstream alighting; never pick a route by number alone."""
    segment, _ = _match_segment_diagnostic(stops, request)
    return segment


def _log_unmatched(request, providers, attempts, reason):
    # One JSON line is easier to filter in Cloud Run. Never include keys or exact coordinates.
    failure_reasons = []
    for attempt in attempts:
        if attempt.get("reason") and attempt["reason"] != "matched":
            failure_reasons.append(attempt["reason"])
        for route in attempt.get("routes", []):
            if route.get("reason") and route["reason"] != "matched":
                failure_reasons.append(route["reason"])
    payload = {
        "event": "transit_route_unmatched",
        "reason": reason,
        "failure_reasons": list(dict.fromkeys(failure_reasons)),
        "route": _route_name(request.route_name),
        "agency": request.agency_name,
        "headsign": request.headsign,
        "departure_stop": request.departure_stop_name,
        "arrival_stop": request.arrival_stop_name,
        "has_departure_location": request.departure_stop_location is not None,
        "has_arrival_location": request.arrival_stop_location is not None,
        "headsign_used_for_matching": False,
        "direction_strategy": "departure_order_before_arrival_order",
        "provider_order": providers,
        "attempts": attempts,
    }
    logger.warning(
        "Transit route resolution failed: %s",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def _log_matched_segment(request, provider, route_id, city_code, details):
    """Google 정류장과 공공데이터 정류장의 매칭 결과를 추적한다."""
    payload = {
        "event": "transit_route_matched",
        "provider": provider,
        "route_id": route_id,
        "city_code": city_code or None,
        "google_route": _route_name(request.route_name),
        "google_departure_stop": request.departure_stop_name,
        "google_arrival_stop": request.arrival_stop_name,
        "google_headsign": request.headsign or None,
        "has_departure_location": request.departure_stop_location is not None,
        "has_arrival_location": request.arrival_stop_location is not None,
        "provider_stop_count": details.get("stop_count"),
        "departure_name_matches": details.get("departure_name_matches"),
        "arrival_name_matches": details.get("arrival_name_matches"),
        "departure_candidates": details.get("departure_candidates"),
        "arrival_candidates": details.get("arrival_candidates"),
        "boarding_order": details.get("boarding_order"),
        "alighting_order": details.get("alighting_order"),
        "boarding_stop_id": details.get("boarding_stop_id"),
        "alighting_stop_id": details.get("alighting_stop_id"),
        "boarding_match_distance_m": details.get("boarding_match_distance_m"),
        "alighting_match_distance_m": details.get("alighting_match_distance_m"),
        "headsign_used_for_matching": False,
        "matching_strategy": "normalized_name_and_coordinate_then_direction_order",
    }
    logger.info(
        "Transit route resolution matched: %s",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def _provider_order(request):
    agency = request.agency_name.lower()
    route = _route_name(request.route_name)
    if "인천" in agency or "incheon" in agency:
        return ["tago"]
    if "서울" in agency or "seoul" in agency or re.match(r"^(N\d|[가-힣]{2,4}\d)", route):
        return ["seoul", "gyeonggi", "tago"]
    return ["gyeonggi", "seoul", "tago"]


def _resolve(request):
    target = _route_name(request.route_name)
    providers = _provider_order(request)
    attempts = []
    had_error = False
    for provider in providers:
        if not _key(provider):
            attempts.append({"provider": provider, "reason": "api_key_not_configured"})
            continue
        city_code = ""
        provider_attempt = {"provider": provider}
        attempts.append(provider_attempt)
        try:
            if provider == "seoul":
                routes = _request(provider, "busRouteInfo", "getBusRouteList",
                                  {"strSrch": target}, "itemList", static=True)
                id_field, name_field = "busRouteId", "busRouteNm"
            elif provider == "gyeonggi":
                routes = _request(provider, "busrouteservice", "getBusRouteList",
                                  {"keyword": target}, "busRouteList", static=True)
                id_field, name_field = "routeId", "routeName"
            else:
                if not request.departure_stop_location:
                    provider_attempt["reason"] = "departure_location_required"
                    continue
                coord = request.departure_stop_location
                nearby = _request(provider, "BusSttnInfoInqireService", "getCrdntPrxmtSttnList",
                                  {"gpsLati": coord.latitude, "gpsLong": coord.longitude}, "item", static=True)
                # Cross-city routes are resolved from static stop/route data, not arrivals.
                city_codes = sorted({_text(item.get("citycode")) for item in nearby if item.get("citycode")})
                candidates = []
                for city in city_codes[:3]:
                    for item in _request(provider, "BusRouteInfoInqireService", "getRouteNoList",
                                         {"cityCode": city, "routeNo": target}, "item", static=True):
                        candidates.append({**item, "_city": city})
                routes = candidates
                id_field, name_field = "routeid", "routeno"
            candidates = [item for item in routes if _route_name(item.get(name_field)) == target]
            provider_attempt["route_results"] = len(routes)
            provider_attempt["exact_route_candidates"] = len(candidates)
            if not candidates:
                provider_attempt["reason"] = "route_not_found"
                continue
            if len(candidates) > 5:
                # Do not accept a seemingly unique match from a truncated candidate set.
                provider_attempt["reason"] = "too_many_route_candidates"
                _log_unmatched(request, providers, attempts, "too_many_route_candidates")
                return None
            matches = []
            route_attempts = []
            provider_attempt["routes"] = route_attempts
            for item in candidates[:5]:
                route_id = _text(item.get(id_field))
                city_code = item.get("_city", "")
                route_attempt = {"route_id": route_id or None}
                route_attempts.append(route_attempt)
                if not route_id:
                    route_attempt["reason"] = "route_id_missing"
                    continue
                # GBIS's search catalog can include Seoul/Incheon. Use their own feeds.
                if provider == "gyeonggi" and str(item.get("districtCd", "2")) != "2":
                    route_attempt["reason"] = "non_gyeonggi_catalog_entry"
                    continue
                stops = _stops(provider, route_id, city_code)
                segment, segment_details = _match_segment_diagnostic(stops, request)
                route_attempt.update(segment_details)
                if segment:
                    matches.append((provider, route_id, city_code, stops, *segment))
            if len(matches) == 1:
                matched_provider, matched_route_id, matched_city_code, _, start, end = matches[0]
                _log_matched_segment(
                    request,
                    matched_provider,
                    matched_route_id,
                    matched_city_code,
                    next(
                        route_attempt
                        for route_attempt in route_attempts
                        if route_attempt.get("route_id") == matched_route_id
                        and route_attempt.get("reason") == "matched"
                    ),
                )
                return matches[0]
            if len(matches) > 1:
                provider_attempt["reason"] = "ambiguous_route_candidates"
                provider_attempt["matched_routes"] = len(matches)
                _log_unmatched(request, providers, attempts, "ambiguous_route_candidates")
                return None
            provider_attempt["reason"] = "no_route_contains_requested_segment"
        except ProviderError:
            # Avoid a cascade of slow calls when an enabled provider is unavailable.
            provider_attempt["reason"] = "provider_error"
            had_error = True
            break
    if had_error:
        raise ProviderError("실시간 제공기관의 API 권한 또는 연결 상태를 확인해주세요.")
    _log_unmatched(request, providers, attempts, "providers_exhausted")
    return None


def _coordinates(item, latitude_keys, longitude_keys):
    try:
        latitude = next(float(item[key]) for key in latitude_keys if item.get(key) not in (None, ""))
        longitude = next(float(item[key]) for key in longitude_keys if item.get(key) not in (None, ""))
    except (StopIteration, TypeError, ValueError):
        return None, None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None, None
    return latitude, longitude


def _vehicle(number, order, stops, *, latitude=None, longitude=None, position_source="stop"):
    stop = next((stop for stop in stops if stop.stop_order == order), None)
    if not number or number == "0" or (not stop and (latitude is None or longitude is None)):
        return []
    if position_source == "stop" and stop:
        latitude, longitude = stop.latitude, stop.longitude
    return [LiveBusPositionResponse(
        vehicle_number=number,
        latitude=latitude,
        longitude=longitude,
        position_source=position_source,
        current_stop_order=order,
        current_stop_id=stop.stop_id if stop else None,
        current_stop_name=stop.stop_name if stop else None,
    )]


def _apply_stop_coordinate_fallback(vehicles, stops):
    """GPS가 없을 때 같은 순번/ID의 정류장 좌표를 차량 위치로 사용한다."""
    stops_by_order = {stop.stop_order: stop for stop in stops}
    stops_by_id = {stop.stop_id: stop for stop in stops}
    enriched = []
    applied = False
    for vehicle in vehicles:
        if vehicle.latitude is not None and vehicle.longitude is not None:
            enriched.append(vehicle)
            continue
        stop = stops_by_order.get(vehicle.current_stop_order)
        if stop is None and vehicle.current_stop_id:
            stop = stops_by_id.get(vehicle.current_stop_id)
        if stop is None or stop.latitude is None or stop.longitude is None:
            enriched.append(vehicle)
            continue
        enriched.append(vehicle.model_copy(update={
            "latitude": stop.latitude,
            "longitude": stop.longitude,
            "position_source": "stop",
            "current_stop_id": stop.stop_id,
            "current_stop_name": stop.stop_name,
        }))
        applied = True
    return enriched, applied


def _log_position_result(provider, route_id, status, reason, vehicles):
    if status == "available":
        return
    payload = {
        "event": "transit_vehicle_position",
        "provider": provider,
        "route_id": route_id,
        "status": status,
        "reason": reason,
        "vehicle_count": len(vehicles),
        "has_coordinates": any(
            vehicle.latitude is not None and vehicle.longitude is not None
            for vehicle in vehicles
        ),
    }
    log = logger.warning if status == "unavailable" else logger.info
    log(
        "Transit vehicle position: %s",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def _read_arrival(provider, route_id, city_code, stops, start):
    """Read the next arrival and the best position precision the provider exposes."""
    if provider == "gyeonggi":
        items = _request(provider, "busarrivalservice", "getBusArrivalItem",
                         {"routeId": route_id, "stationId": start.stop_id, "staOrder": start.stop_order},
                         "busArrivalItem")
        item = items[0] if items else {}
        minutes = _number(item.get("predictTime1"))
        seconds = _number(item.get("predictTimeSec1"))
        number = _text(item.get("plateNo1"))
        if item.get("flag") in {"STOP", "WAIT"} or not number or (minutes is None and seconds is None):
            return (None, None, [], item.get("_fetched_at"), "unavailable",
                    "no_active_arrival_vehicle",
                    "현재 운행 중인 다음 차량의 위치가 제공되지 않습니다.")
        if seconds is not None and seconds >= 0:
            minutes = math.ceil(seconds / 60)
        remaining = _number(item.get("locationNo1"))
        order = start.stop_order - remaining if remaining is not None and remaining >= 0 else None
        vehicles = _vehicle(number, order, stops, position_source="stop")
        if vehicles and vehicles[0].latitude is not None:
            status, reason = "fallback", "provider_stop_level_only"
            position_message = "경기도는 정류장 기준 차량 위치를 제공합니다."
        elif vehicles:
            status, reason = "fallback", "stop_coordinates_missing"
            position_message = "차량의 현재 정류장은 확인했지만 지도 좌표가 없습니다."
        else:
            status, reason = "unavailable", "arrival_position_fields_missing"
            position_message = "도착정보에 차량의 현재 정류장 순번이 없습니다."
        return (minutes if minutes is not None and minutes >= 0 else None, None,
                vehicles, item.get("_fetched_at"), status, reason, position_message)
    if provider == "seoul":
        # All stops on a route share one cached arrival response.
        items = _request(provider, "arrive", "getArrInfoByRouteAll", {"busRouteId": route_id}, "itemList")
        item = next((item for item in items
                     if _text(item.get("stId")) == start.stop_id
                     and _number(item.get("staOrd")) == start.stop_order), {})
        message = _text(item.get("arrmsg1"))
        if not message or any(word in message for word in ("출발대기", "운행종료", "정보없음")):
            return (None, message or None, [], item.get("_fetched_at"),
                    "unavailable", "no_active_arrival_vehicle",
                    "현재 운행 중인 다음 차량의 위치가 제공되지 않습니다.")
        # arrmsg is the public-facing prediction; exps/kals are internal estimates.
        match = re.search(r"(\d+)분(?:\s*(\d+)초)?", message)
        seconds_match = re.search(r"(\d+)초", message)
        minutes = (math.ceil((int(match[1]) * 60 + int(match[2] or 0)) / 60) if match
                   else math.ceil(int(seconds_match[1]) / 60) if seconds_match
                   else 0 if "곧 도착" in message else None)
        vehicle_id = _text(item.get("vehId1"))
        fallback = _vehicle(vehicle_id, _number(item.get("sectOrd1")), stops,
                            position_source="stop")
        try:
            positions = _request(
                provider,
                "buspos",
                "getBusPosByRouteSt",
                {"busRouteId": route_id, "startOrd": 1, "endOrd": start.stop_order},
                "itemList",
            )
        except ProviderError:
            status = "fallback" if fallback else "unavailable"
            return (minutes, message, fallback, item.get("_fetched_at"), status,
                    "location_api_failed",
                    "서울 버스 위치 API 권한 또는 연결 상태를 확인해주세요.")
        position = next(
            (position for position in positions if _text(position.get("vehId")) == vehicle_id),
            None,
        )
        if position:
            latitude, longitude = _coordinates(position, ("posY", "tmY"), ("posX", "tmX"))
            precise = _vehicle(
                _text(position.get("plainNo")) or vehicle_id,
                _number(position.get("sectOrd")),
                stops,
                latitude=latitude,
                longitude=longitude,
                position_source="map_matched" if latitude is not None else "stop",
            )
            if precise and latitude is not None:
                return (minutes, message, precise, position.get("_fetched_at") or item.get("_fetched_at"),
                        "available", "map_matched_coordinates", "도로에 보정된 실시간 차량 위치입니다.")
            if precise:
                return (minutes, message, precise, position.get("_fetched_at") or item.get("_fetched_at"),
                        "fallback", "location_coordinates_missing",
                        "차량은 확인했지만 좌표가 없어 정류장 기준으로 표시합니다.")
        status = "fallback" if fallback else "unavailable"
        return (minutes, message, fallback, item.get("_fetched_at"), status,
                "arrival_vehicle_not_in_location_feed",
                "다음 차량을 위치정보 목록에서 찾지 못해 정류장 기준으로 표시합니다.")
    items = _request(provider, "ArvlInfoInqireService", "getSttnAcctoArvlPrearngeInfoList",
                     {"cityCode": city_code, "nodeId": start.stop_id}, "item")
    arrivals = [item for item in items if _text(item.get("routeid")) == route_id
                and _number(item.get("arrtime")) is not None and int(item["arrtime"]) >= 0]
    if not arrivals:
        return (None, None, [], None, "unavailable", "no_active_arrival_vehicle",
                "현재 운행 중인 다음 차량의 위치가 제공되지 않습니다.")
    first = min(arrivals, key=lambda item: int(item["arrtime"]))
    # Arrival lacks a vehicle ID. Do not invent a vehicle match/position from proximity.
    try:
        positions = _request(provider, "BusLcInfoInqireService", "getRouteAcctoBusLcList",
                             {"cityCode": city_code, "routeId": route_id}, "item")
    except ProviderError:
        # Location permission/outages must not hide a successfully fetched ETA.
        return (math.ceil(int(first["arrtime"]) / 60), None, [], first.get("_fetched_at"),
                "unavailable", "location_api_failed",
                "TAGO 버스 위치 API 권한 또는 연결 상태를 확인해주세요.")
    approaching = [
        item for item in positions
        if _number(item.get("nodeord")) is not None
        and _number(item.get("nodeord")) <= start.stop_order
    ]
    position = max(approaching, key=lambda item: _number(item.get("nodeord")), default=None)
    if not position:
        return (math.ceil(int(first["arrtime"]) / 60), None, [], first.get("_fetched_at"),
                "unavailable", "no_approaching_vehicle_in_location_feed",
                "탑승 정류장으로 접근 중인 차량을 위치정보에서 찾지 못했습니다.")
    latitude, longitude = _coordinates(position, ("gpslati",), ("gpslong",))
    vehicles = _vehicle(
        _text(position.get("vehicleno")),
        _number(position.get("nodeord")),
        stops,
        latitude=latitude,
        longitude=longitude,
        position_source="gps" if latitude is not None else "stop",
    )
    if vehicles and latitude is not None:
        status, reason = "available", "gps_coordinates"
        position_message = "GPS 기반 실시간 차량 위치입니다."
    elif vehicles:
        status, reason = "fallback", "location_coordinates_missing"
        position_message = "GPS 좌표가 없어 현재 정류장 기준으로 표시합니다."
    else:
        status, reason = "unavailable", "location_vehicle_fields_missing"
        position_message = "위치정보 응답에서 차량을 식별하지 못했습니다."
    return (math.ceil(int(first["arrtime"]) / 60), None, vehicles,
            position.get("_fetched_at") or first.get("_fetched_at"),
            status, reason, position_message)


def _result(status, **kwargs):
    kwargs.setdefault("cached_at", datetime.now(timezone.utc))
    return TransitLiveResponse(status=status, **kwargs)


def get_transit_live(request: TransitLiveRequest):
    if "BUS" not in request.vehicle_type.upper():
        return _result("unsupported", refresh_after_seconds=STATIC_TTL,
                       message="이 구간은 예정 시간으로 안내합니다.",
                       vehicle_position_status="not_applicable",
                       vehicle_position_reason="unsupported_vehicle_type")
    if not any(_key(provider) for provider in _provider_order(request)):
        return _result("not_configured", refresh_after_seconds=STATIC_TTL,
                       message="실시간 정보 연결이 준비되지 않았습니다.",
                       vehicle_position_reason="provider_api_key_not_configured")
    descriptor = request.model_dump_json()
    try:
        resolved = _cache.get(("resolve", descriptor), lambda: _resolve(request),
                              ttl=STATIC_TTL, empty_ttl=EMPTY_TTL, error_ttl=FAILURE_TTL)
    except ProviderError:
        return _result("provider_error", refresh_after_seconds=FAILURE_TTL,
                       message="실시간 정보를 잠시 불러올 수 없습니다.",
                       vehicle_position_reason="route_resolution_failed")
    if not resolved:
        return _result("unmatched", refresh_after_seconds=STATIC_TTL,
                       message="이 구간의 정류장과 운행 방향을 확인하지 못했습니다.",
                       vehicle_position_reason="route_not_matched")
    provider, route_id, city_code, stops, start, end = resolved

    def load():
        common = dict(provider=provider, route_stops=stops,
                      boarding_stop_order=start.stop_order, alighting_stop_order=end.stop_order)
        try:
            (minutes, message, vehicles, fetched_at, position_status,
             position_reason, position_message) = _read_arrival(
                provider, route_id, city_code, stops, start
            )
        except ProviderError:
            return _result("provider_error", **common, refresh_after_seconds=FAILURE_TTL,
                           message="정류장 정보는 확인했지만 실시간 조회에 실패했습니다.",
                           vehicle_position_reason="arrival_api_failed",
                           vehicle_position_message="도착정보 API 권한 또는 연결 상태를 확인해주세요.")
        had_coordinates = any(
            vehicle.latitude is not None and vehicle.longitude is not None
            for vehicle in vehicles
        )
        vehicles, fallback_applied = _apply_stop_coordinate_fallback(vehicles, stops)
        if fallback_applied and not had_coordinates:
            position_status = "fallback"
            position_reason = "stop_coordinate_fallback"
            position_message = "GPS 좌표가 없어 현재 정류장 위치에 차량을 표시합니다."
        _log_position_result(provider, route_id, position_status, position_reason, vehicles)
        return _result("ok" if minutes is not None or vehicles else "no_data", **common,
                       cached_at=fetched_at or datetime.now(timezone.utc),
                       arrival_minutes=minutes, arrival_message=message, vehicles=vehicles,
                       vehicle_number=vehicles[0].vehicle_number if len(vehicles) == 1 else None,
                       vehicle_position_status=position_status,
                       vehicle_position_reason=position_reason,
                       vehicle_position_message=position_message,
                       refresh_after_seconds=LIVE_TTL if minutes is not None or vehicles else EMPTY_TTL,
                       message=None if minutes is not None else "현재 도착 예정을 제공하지 않습니다.")

    # Cache failures/empty envelopes for their advertised backoff, not just HTTP data.
    cache_key = ("live", provider, city_code, route_id, start.stop_order, end.stop_order)
    result = _cache.get(cache_key, load, ttl=lambda result: result.refresh_after_seconds)
    return result
