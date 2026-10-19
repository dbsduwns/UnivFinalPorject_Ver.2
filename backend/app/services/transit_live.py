"""지연 방식의 대중교통 실시간 정보 보강 모듈.

경로 예측 서비스에서는 호출하지 않는다. 정적 노선 매칭은 6시간,
실시간 조회 결과는 30초, 빈 응답은 2분, 실패 결과는 1분 동안 공유한다.
정류장 목록이 펼쳐져 있을 때만 호출하며, 노선 단위 위치 API 결과를 캐시해
화면에서 경로 전체 차량의 현재 정류장을 표시한다.
"""

from datetime import datetime, timezone
import json
import logging
import math
import os
import re
from threading import Lock
from time import monotonic
from urllib.parse import quote, unquote
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
DISPLAY_BEFORE_BOARDING_STOP_COUNT = 5
DISPLAY_AFTER_ALIGHTING_STOP_COUNT = 3
# 서울 버스 api URL
SEOUL_BUS_API_BASE_URL = "http://ws.bus.go.kr/api/rest"
# 서울 열린데이터광장의 해당 지하철 API는 공식적으로 HTTP 8088 포트만 제공한다.
SEOUL_SUBWAY_API_BASE_URL = "http://openapi.seoul.go.kr:8088"
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
    # 포털에서 같은 키를 사용하더라도 새 API는 별도로 활성화해야 한다.
    # 명시적으로 활성화한 제공기관만 사용해 계정에서 사용할 수 없는 API를 반복 호출하지 않는다.
    return os.getenv(f"{provider.upper()}_BUS_API_KEY") or (
        os.getenv("PUBLIC_API_KEY") if provider == "tago" else None
    )


def _subway_key():
    """서울교통공사 지하철 정적 API 전용 인증키를 반환한다."""
    return os.getenv("SEOUL_SUBWAY_API_KEY")


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


def _relaxed_route_name_match(value, target):
    """노선명 뒤에 붙은 방면 표기를 허용하되 다른 번호 노선은 제외한다."""
    candidate = _route_name(value)
    if not candidate.startswith(target) or candidate == target:
        return False
    suffix = candidate[len(target):]
    return bool(suffix) and not suffix[0].isdigit() and suffix[0] not in "-_"


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


def _subway_line_name(value):
    """Google 노선명을 서울교통공사 노선 검색용 이름으로 정규화한다."""
    normalized = _text(value).replace("호선", "").replace("Line", "").replace("line", "")
    return re.sub(r"\s+", "", normalized)


def _subway_stations(line_name):
    """서울교통공사 노선별 역 목록을 캐시해 반환한다."""
    key = _subway_key()
    if not key:
        raise ProviderError("서울 지하철 API 키가 설정되지 않았습니다.", reason="api_key_not_configured")
    cache_key = ("subway_stations", _subway_line_name(line_name))

    def load():
        line = _subway_line_name(line_name)
        url = (
            f"{SEOUL_SUBWAY_API_BASE_URL}/{quote(unquote(key), safe='')}/json/"
            f"SearchSTNBySubwayLineInfo/1/1000///{quote(line, safe='')}"
        )
        try:
            response = requests.get(url, timeout=(2, 5))
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("지하철 정적 노선 API 요청 실패: reason=%s", type(exc).__name__)
            raise ProviderError("지하철 노선 정보를 불러오지 못했습니다.", reason="subway_static_api_failed") from exc
        envelope = data.get("SearchSTNBySubwayLineInfo") or {}
        result = envelope.get("RESULT") or {}
        if result and _text(result.get("CODE")) not in {"INFO-000", "INFO-200"}:
            raise ProviderError("지하철 노선 API 응답 오류입니다.", reason="subway_static_result_error")
        rows = envelope.get("row") or []
        if isinstance(rows, dict):
            rows = [rows]
        stops = []
        for order, row in enumerate(rows, start=1):
            station_id = _text(row.get("STATION_CD") or row.get("FR_CODE"))
            station_name = _text(row.get("STATION_NM"))
            if station_id and station_name:
                stops.append(RouteStopResponse(
                    stop_order=order,
                    stop_id=station_id,
                    stop_name=station_name,
                ))
        if not stops:
            raise ProviderError("지하철 노선에 역 정보가 없습니다.", reason="subway_stations_empty")
        return stops

    return _cache.get(cache_key, load, ttl=STATIC_TTL, empty_ttl=EMPTY_TTL, error_ttl=FAILURE_TTL)


def _request(provider, service, operation, params, item_key, static=False):
    """제공기관 조회를 캐시해 여러 사용자와 경로 구간이 결과를 공유하도록 한다."""
    cache_key = (provider, service, operation, tuple(sorted(params.items())))

    def load():
        api_key = _key(provider)
        if not api_key:
            raise ProviderError("실시간 API 키가 설정되지 않았습니다.")
        # 인증·할당량 실패가 정류장마다 새 요청을 발생시키지 않도록 한다.
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
            # URL이나 예외에 인증키가 포함될 수 있으므로 안전한 분류 정보만 기록한다.
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
                "route_id=%s reason=%s http_status=%s result_code=%s",
                provider,
                service,
                operation,
                _text(params.get("routeId") or params.get("busRouteId")) or None,
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
        # 200m 이내 매칭 여부를 판단하기에 충분한 지역 거리 근사값이다.
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
    """방향이 맞는 경로 구간과 민감정보를 제외한 매칭 진단 정보를 반환한다."""
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
    # 순환 노선에서는 같은 이름·좌표의 정류장이 양방향에 존재할 수 있으므로 동점은 거부한다.
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
    """탑승 정류장과 이후 하차 정류장을 모두 확인하며 노선 번호만으로 선택하지 않는다."""
    segment, _ = _match_segment_diagnostic(stops, request)
    return segment


def _log_unmatched(request, providers, attempts, reason):
    # Cloud Run에서 한 줄 JSON이 필터링하기 쉽다. 키나 정확한 좌표는 절대 기록하지 않는다.
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


def _resolve_subway(request):
    """Google 지하철 구간을 서울교통공사 정적 역 순서로 매칭한다."""
    stops = _subway_stations(request.route_name)
    segment, _ = _match_segment_diagnostic(stops, request)
    if segment:
        return "seoul_subway", _subway_line_name(request.route_name), "", stops, *segment
    reversed_stops = [
        stop.model_copy(update={"stop_order": index})
        for index, stop in enumerate(reversed(stops), start=1)
    ]
    segment, _ = _match_segment_diagnostic(reversed_stops, request)
    if segment:
        return "seoul_subway", _subway_line_name(request.route_name), "", reversed_stops, *segment
    return None


def _resolve(request):
    if "SUBWAY" in request.vehicle_type.upper():
        return _resolve_subway(request)
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
                # 광역 노선은 도착정보가 아닌 정적 정류장·노선 데이터로 확인한다.
                city_codes = sorted({_text(item.get("citycode")) for item in nearby if item.get("citycode")})
                candidates = []
                for city in city_codes[:3]:
                    for item in _request(provider, "BusRouteInfoInqireService", "getRouteNoList",
                                         {"cityCode": city, "routeNo": target}, "item", static=True):
                        candidates.append({**item, "_city": city})
                routes = candidates
                id_field, name_field = "routeid", "routeno"
            route_names = [_text(item.get(name_field)) for item in routes if item.get(name_field)]
            exact_candidates = [item for item in routes if _route_name(item.get(name_field)) == target]
            candidates = exact_candidates
            match_type = "exact" if exact_candidates else None
            if not exact_candidates:
                relaxed = [
                    item for item in routes
                    if _relaxed_route_name_match(item.get(name_field), target)
                ]
                # 부가 방면 표기가 붙은 후보가 하나일 때만 안전하게 보정 매칭한다.
                if len(relaxed) == 1:
                    candidates = relaxed
                    match_type = "normalized_suffix"
            provider_attempt["route_results"] = len(routes)
            provider_attempt["route_names"] = route_names[:10]
            provider_attempt["exact_route_candidates"] = len(exact_candidates)
            provider_attempt["matched_route_candidates"] = len(candidates)
            provider_attempt["route_match_type"] = match_type
            if not candidates:
                provider_attempt["reason"] = "route_not_found"
                continue
            if len(candidates) > 5:
                # 후보 목록이 잘린 상태에서는 유일해 보이는 매칭도 채택하지 않는다.
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
                # GBIS 검색 목록에는 서울·인천 노선이 포함될 수 있으므로 자체 제공기관 데이터를 사용한다.
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
            # 활성화된 제공기관에 연결할 수 없을 때 느린 요청이 연쇄적으로 발생하지 않도록 한다.
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


def _log_position_result(provider, route_id, route_name, status, reason, vehicles):
    payload = {
        "event": "transit_vehicle_position",
        "provider": provider,
        "route_id": route_id,
        "route_name": route_name,
        "status": status,
        "reason": reason,
        "vehicle_count": len(vehicles),
        "vehicles": [
            {
                "vehicle_number": vehicle.vehicle_number,
                "current_stop_id": vehicle.current_stop_id,
                "current_stop_name": vehicle.current_stop_name,
                "current_stop_order": vehicle.current_stop_order,
                "latitude": vehicle.latitude,
                "longitude": vehicle.longitude,
                "position_source": vehicle.position_source,
            }
            for vehicle in vehicles
        ],
        "has_coordinates": any(vehicle.latitude is not None and vehicle.longitude is not None
                               for vehicle in vehicles),
    }
    log = logger.warning if status == "unavailable" else logger.info
    log(
        "Transit vehicle position: %s",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def _read_arrival(provider, route_id, city_code, stops, start, end):
    """다음 도착정보와 제공기관이 제공하는 가장 정확한 위치 정밀도를 읽는다."""
    if provider == "gyeonggi":
        items = _request(provider, "busarrivalservice", "getBusArrivalItem",
                         {"routeId": route_id, "stationId": start.stop_id, "staOrder": start.stop_order},
                         "busArrivalItem")
        item = items[0] if items else {}
        minutes = _number(item.get("predictTime1"))
        seconds = _number(item.get("predictTimeSec1"))
        number = _text(item.get("plateNo1"))
        has_arrival = bool(number and item.get("flag") not in {"STOP", "WAIT"}
                           and (minutes is not None or seconds is not None))
        if seconds is not None and seconds >= 0:
            minutes = math.ceil(seconds / 60)
        remaining = _number(item.get("locationNo1"))
        order = start.stop_order - remaining if remaining is not None and remaining >= 0 else None
        arrival_vehicle = _vehicle(number, order, stops, position_source="stop") if has_arrival else []
        try:
            positions = _request(
                provider, "buslocationservice", "getBusLocationList",
                {"routeId": route_id}, "busLocationList",
            )
        except ProviderError:
            if arrival_vehicle:
                return (minutes, None, arrival_vehicle, item.get("_fetched_at"),
                        "fallback", "location_api_failed_using_arrival_data",
                        "전체 차량 위치 조회에 실패해 도착정보의 차량만 표시합니다.")
            raise
        vehicles = []
        for position in positions:
            stop_id = _text(position.get("stationId"))
            stop_order = _number(position.get("stationSeq"))
            if stop_order is None and stop_id:
                matched_stop = next((stop for stop in stops if stop.stop_id == stop_id), None)
                stop_order = matched_stop.stop_order if matched_stop else None
            vehicles.extend(_vehicle(
                _text(position.get("plateNo")) or _text(position.get("vehId")),
                stop_order,
                stops,
                position_source="stop",
            ))
        known_numbers = {vehicle.vehicle_number for vehicle in vehicles}
        vehicles.extend(vehicle for vehicle in arrival_vehicle
                        if vehicle.vehicle_number not in known_numbers)
        if vehicles:
            return (minutes if minutes is not None and minutes >= 0 else None, None,
                    vehicles, positions[0].get("_fetched_at") if positions else item.get("_fetched_at"),
                    "fallback", "provider_stop_level_only",
                    "경기도 버스 위치정보 API의 차량별 정류장을 표시합니다.")
        if positions and not vehicles:
            reason = "vehicle_location_records_unmatched_to_route_stops"
            message = "차량 위치 응답은 받았지만 정류장 순번·ID가 노선 정류장과 일치하지 않습니다."
        elif has_arrival and not arrival_vehicle:
            reason = "arrival_position_fields_missing"
            message = "도착 차량은 확인했지만 해당 위치를 노선 정류장과 연결하지 못했습니다."
        else:
            reason = "no_vehicle_records_for_route"
            message = "해당 노선의 실시간 차량 위치 정보가 없습니다."
        return (minutes if minutes is not None and minutes >= 0 else None, None,
                [], positions[0].get("_fetched_at") if positions else item.get("_fetched_at"),
                "unavailable", reason, message)
    if provider == "seoul":
        # 한 노선의 모든 정류장은 하나의 캐시된 도착 응답을 공유한다.
        items = _request(provider, "arrive", "getArrInfoByRouteAll", {"busRouteId": route_id}, "itemList")
        item = next((item for item in items
                     if _text(item.get("stId")) == start.stop_id
                     and _number(item.get("staOrd")) == start.stop_order), {})
        message = _text(item.get("arrmsg1"))
        if not message or any(word in message for word in ("출발대기", "운행종료", "정보없음")):
            return (None, message or None, [], item.get("_fetched_at"),
                    "unavailable", "no_active_arrival_vehicle",
                    "현재 운행 중인 다음 차량의 위치가 제공되지 않습니다.")
        # arrmsg는 사용자에게 표시할 예측값이고 exps·kals는 내부 추정값이다.
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
                {"busRouteId": route_id, "startOrd": 1,
                 "endOrd": max((stop.stop_order for stop in stops), default=end.stop_order)},
                "itemList",
            )
        except ProviderError:
            status = "fallback" if fallback else "unavailable"
            return (minutes, message, fallback, item.get("_fetched_at"), status,
                    "location_api_failed",
                    "서울 버스 위치 API 권한 또는 연결 상태를 확인해주세요.")
        all_vehicles = []
        for position in positions:
            position_order = _number(position.get("sectOrd"))
            latitude, longitude = _coordinates(position, ("posY", "tmY"), ("posX", "tmX"))
            all_vehicles.extend(_vehicle(
                _text(position.get("plainNo")) or _text(position.get("vehId")),
                _number(position.get("sectOrd")),
                stops,
                latitude=latitude,
                longitude=longitude,
                position_source="map_matched" if latitude is not None else "stop",
            ))
        # 위치 목록에 없거나 중복으로 포함된 도착 예정 차량은 한 번만 유지한다.
        known_numbers = {vehicle.vehicle_number for vehicle in all_vehicles}
        position_ids = {_text(position.get("vehId")) for position in positions}
        all_vehicles.extend(
            vehicle for vehicle in fallback
            if vehicle.vehicle_number not in known_numbers
            and vehicle.vehicle_number not in position_ids
        )
        if all_vehicles:
            has_coordinates = any(
                vehicle.latitude is not None and vehicle.longitude is not None
                for vehicle in all_vehicles
            )
            return (minutes, message, all_vehicles,
                    next((vehicle.get("_fetched_at") for vehicle in positions if vehicle.get("_fetched_at")), None)
                    or item.get("_fetched_at"),
                    "available" if has_coordinates else "fallback",
                    "map_matched_coordinates" if has_coordinates else "location_coordinates_missing",
                    "노선 전체 차량의 GPS 위치를 표시합니다." if has_coordinates
                    else "차량은 확인했지만 좌표가 없어 정류장 기준으로 표시합니다.")
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
    # 도착정보에 차량 ID가 없으므로 근접성만으로 차량 매칭·위치를 추정하지 않는다.
    try:
        positions = _request(provider, "BusLcInfoInqireService", "getRouteAcctoBusLcList",
                             {"cityCode": city_code, "routeId": route_id}, "item")
    except ProviderError:
        # 위치 API 권한이나 장애 때문에 정상적으로 받은 도착 예정시간을 숨기지 않는다.
        return (math.ceil(int(first["arrtime"]) / 60), None, [], first.get("_fetched_at"),
                "unavailable", "location_api_failed",
                "TAGO 버스 위치 API 권한 또는 연결 상태를 확인해주세요.")
    same_direction = [
        item for item in positions
        if _number(item.get("nodeord")) is not None
        and _number(item.get("nodeord")) <= max((stop.stop_order for stop in stops), default=end.stop_order)
    ]
    if not same_direction:
        return (math.ceil(int(first["arrtime"]) / 60), None, [], first.get("_fetched_at"),
                "unavailable", "no_vehicle_in_route_location_feed",
                "노선 위치정보에서 차량을 찾지 못했습니다.")
    vehicles = []
    for position in same_direction:
        latitude, longitude = _coordinates(position, ("gpslati",), ("gpslong",))
        vehicles.extend(_vehicle(
            _text(position.get("vehicleno")),
            _number(position.get("nodeord")),
            stops,
            latitude=latitude,
            longitude=longitude,
            position_source="gps" if latitude is not None else "stop",
        ))
    has_coordinates = any(
        vehicle.latitude is not None and vehicle.longitude is not None
        for vehicle in vehicles
    )
    if vehicles and has_coordinates:
        status, reason = "available", "gps_coordinates"
        position_message = "노선 전체 차량의 GPS 위치입니다."
    elif vehicles:
        status, reason = "fallback", "location_coordinates_missing"
        position_message = "GPS 좌표가 없어 현재 정류장 기준으로 표시합니다."
    else:
        status, reason = "unavailable", "location_vehicle_fields_missing"
        position_message = "위치정보 응답에서 차량을 식별하지 못했습니다."
    return (math.ceil(int(first["arrtime"]) / 60), None, vehicles,
            same_direction[0].get("_fetched_at") or first.get("_fetched_at"),
            status, reason, position_message)


def _result(status, **kwargs):
    kwargs.setdefault("cached_at", datetime.now(timezone.utc))
    return TransitLiveResponse(status=status, **kwargs)


def _display_stops(stops, start, end):
    """탑승 전 5개부터 하차 후 3개까지의 연속된 정류장 구간을 반환한다."""
    ordered_stops = sorted(stops, key=lambda stop: stop.stop_order)
    start_index = next((index for index, stop in enumerate(ordered_stops)
                        if stop.stop_order == start.stop_order and stop.stop_id == start.stop_id), None)
    end_index = next((index for index, stop in enumerate(ordered_stops)
                      if stop.stop_order == end.stop_order and stop.stop_id == end.stop_id), None)
    if start_index is None or end_index is None:
        return ordered_stops
    first_index = max(0, min(start_index, end_index) - DISPLAY_BEFORE_BOARDING_STOP_COUNT)
    last_index = min(len(ordered_stops), max(start_index, end_index) + DISPLAY_AFTER_ALIGHTING_STOP_COUNT + 1)
    return ordered_stops[first_index:last_index]


def get_transit_live(request: TransitLiveRequest):
    vehicle_type = request.vehicle_type.upper()
    if "BUS" not in vehicle_type and "SUBWAY" not in vehicle_type:
        return _result("unsupported", refresh_after_seconds=STATIC_TTL,
                       message="이 구간은 예정 시간으로 안내합니다.",
                       vehicle_position_status="not_applicable",
                       vehicle_position_reason="unsupported_vehicle_type")
    configured = _subway_key() if "SUBWAY" in vehicle_type else any(
        _key(provider) for provider in _provider_order(request)
    )
    if not configured:
        logger.warning(
            "Transit vehicle lookup failed: %s",
            json.dumps({
                "event": "transit_vehicle_lookup_failed",
                "stage": "configuration",
                "route_name": request.route_name,
                "reason": "provider_api_key_not_configured",
            }, ensure_ascii=False, separators=(",", ":")),
        )
        return _result("not_configured", refresh_after_seconds=STATIC_TTL,
                       message="실시간 정보 연결이 준비되지 않았습니다.",
                       vehicle_position_reason="provider_api_key_not_configured")
    descriptor = request.model_dump_json()
    try:
        resolved = _cache.get(("resolve", descriptor), lambda: _resolve(request),
                              ttl=STATIC_TTL, empty_ttl=EMPTY_TTL, error_ttl=FAILURE_TTL)
    except ProviderError:
        logger.exception(
            "Transit vehicle lookup failed: %s",
            json.dumps({
                "event": "transit_vehicle_lookup_failed",
                "stage": "route_resolution",
                "route_name": request.route_name,
                "reason": "route_resolution_failed",
            }, ensure_ascii=False, separators=(",", ":")),
        )
        return _result("provider_error", refresh_after_seconds=FAILURE_TTL,
                       message="실시간 정보를 잠시 불러올 수 없습니다.",
                       vehicle_position_reason="route_resolution_failed")
    if not resolved:
        logger.warning(
            "Transit vehicle lookup failed: %s",
            json.dumps({
                "event": "transit_vehicle_lookup_failed",
                "stage": "route_resolution",
                "route_name": request.route_name,
                "departure_stop": request.departure_stop_name,
                "arrival_stop": request.arrival_stop_name,
                "reason": "route_not_matched",
            }, ensure_ascii=False, separators=(",", ":")),
        )
        return _result("unmatched", refresh_after_seconds=STATIC_TTL,
                       message="이 구간의 정류장과 운행 방향을 확인하지 못했습니다.",
                       vehicle_position_reason="route_not_matched")
    provider, route_id, city_code, stops, start, end = resolved
    displayed_stops = _display_stops(stops, start, end)
    if provider == "seoul_subway":
        return _result(
            "unsupported",
            provider=provider,
            route_stops=displayed_stops,
            boarding_stop_order=start.stop_order,
            alighting_stop_order=end.stop_order,
            vehicle_position_status="not_applicable",
            vehicle_position_reason="subway_realtime_not_connected",
            vehicle_position_message="지하철 실시간 API 연결 전 정적 역 목록을 표시합니다.",
            refresh_after_seconds=STATIC_TTL,
            message="지하철 실시간 위치는 다음 단계에서 연결합니다.",
        )

    def load():
        common = dict(provider=provider, route_stops=displayed_stops,
                      boarding_stop_order=start.stop_order, alighting_stop_order=end.stop_order)
        try:
            (minutes, message, vehicles, fetched_at, position_status,
             position_reason, position_message) = _read_arrival(
                provider, route_id, city_code, stops, start, end
            )
        except ProviderError:
            logger.exception(
                "Transit vehicle lookup failed: %s",
                json.dumps({
                    "event": "transit_vehicle_lookup_failed",
                    "stage": "arrival_or_position_api",
                    "provider": provider,
                    "route_id": route_id,
                    "route_name": request.route_name,
                    "reason": "provider_api_failed",
                }, ensure_ascii=False, separators=(",", ":")),
            )
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
        _log_position_result(
            provider, route_id, request.route_name,
            position_status, position_reason, vehicles,
        )
        return _result("ok" if minutes is not None or vehicles else "no_data", **common,
                       cached_at=fetched_at or datetime.now(timezone.utc),
                       arrival_minutes=minutes, arrival_message=message, vehicles=vehicles,
                       vehicle_number=vehicles[0].vehicle_number if len(vehicles) == 1 else None,
                       vehicle_position_status=position_status,
                       vehicle_position_reason=position_reason,
                       vehicle_position_message=position_message,
                       refresh_after_seconds=LIVE_TTL if minutes is not None or vehicles else EMPTY_TTL,
                       message=None if minutes is not None else "현재 도착 예정을 제공하지 않습니다.")

    # HTTP 데이터뿐 아니라 실패·빈 응답도 지정된 재시도 대기시간만큼 캐시한다.
    cache_key = ("live", provider, city_code, route_id, start.stop_order, end.stop_order)
    try:
        return _cache.get(cache_key, load, ttl=lambda result: result.refresh_after_seconds)
    except Exception as exc:
        logger.exception(
            "Transit vehicle lookup failed: %s",
            json.dumps({
                "event": "transit_vehicle_lookup_failed",
                "stage": "position_processing",
                "provider": provider,
                "route_id": route_id,
                "route_name": request.route_name,
                "exception_type": type(exc).__name__,
            }, ensure_ascii=False, separators=(",", ":")),
        )
        return _result(
            "provider_error",
            provider=provider,
            route_stops=displayed_stops,
            boarding_stop_order=start.stop_order,
            alighting_stop_order=end.stop_order,
            refresh_after_seconds=FAILURE_TTL,
            message="차량 위치 처리 중 오류가 발생했습니다.",
            vehicle_position_status="unavailable",
            vehicle_position_reason="position_processing_failed",
            vehicle_position_message="오류 로그에서 실패 단계를 확인해주세요.",
        )
