"""Cloud Run Job용 경기도 버스 API 연결 진단 스크립트.

필수 환경변수:
    GYEONGGI_BUS_API_KEY

예시:
    python scripts/test_gyeonggi_bus_api.py --route 5000

API 키와 요청 URL의 serviceKey 값은 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from time import monotonic
from urllib.parse import unquote

import requests


BASE_URL = "https://apis.data.go.kr/6410000"
DEFAULT_TIMEOUT = (5, 5)


class ApiCheckError(RuntimeError):
    """공공 API 응답이 예상과 다를 때 사용하는 진단 오류."""


def _text(value: object) -> str:
    return str(value if value is not None else "").strip()


def _items(value: object) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _message(response: requests.Response) -> tuple[str, str, dict]:
    try:
        data = response.json()
    except ValueError as exc:
        raise ApiCheckError(
            f"응답이 JSON이 아닙니다. http_status={response.status_code}"
        ) from exc

    envelope = data.get("response", data)
    if not isinstance(envelope, dict):
        raise ApiCheckError("응답의 response 구조를 찾지 못했습니다.")

    header = envelope.get("msgHeader") or {}
    body = envelope.get("msgBody") or {}
    code = _text(header.get("resultCode"))
    message = _text(header.get("resultMessage"))
    if code not in {"0", "00", "4"}:
        raise ApiCheckError(
            f"경기 API 오류: result_code={code or None} "
            f"result_message={message or None}"
        )
    if not isinstance(body, dict):
        body = {}
    return code, message, body


def _request(
    api_key: str,
    service: str,
    operation: str,
    params: dict[str, object],
) -> tuple[str, str, dict, float]:
    url = f"{BASE_URL}/{service}/v2/{operation}v2"
    query = {
        "serviceKey": unquote(api_key),
        "format": "json",
        **params,
    }
    started = monotonic()
    try:
        response = requests.get(url, params=query, timeout=DEFAULT_TIMEOUT)
        elapsed = monotonic() - started
        response.raise_for_status()
    except requests.Timeout as exc:
        elapsed = monotonic() - started
        raise ApiCheckError(
            f"timeout: service={service} operation={operation} "
            f"elapsed_seconds={elapsed:.3f}"
        ) from exc
    except requests.RequestException as exc:
        elapsed = monotonic() - started
        raise ApiCheckError(
            f"network/http error: service={service} operation={operation} "
            f"elapsed_seconds={elapsed:.3f} "
            f"http_status={getattr(exc.response, 'status_code', None)}"
        ) from exc

    code, message, body = _message(response)
    return code, message, body, elapsed


def _select_route(routes: list[dict], keyword: str) -> dict:
    exact = [
        route for route in routes
        if _text(route.get("routeName")) == keyword
    ]
    candidates = exact or routes
    if not candidates:
        raise ApiCheckError(f"노선 검색 결과가 없습니다: keyword={keyword}")

    yongin = [
        route for route in candidates
        if "용인" in _text(route.get("adminName"))
    ]
    return (yongin or candidates)[0]


def _print_check(label: str, *, elapsed: float, **details: object) -> None:
    print(json.dumps({
        "check": label,
        "ok": True,
        "elapsed_seconds": round(elapsed, 3),
        **details,
    }, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Gyeonggi bus API from Cloud Run.")
    parser.add_argument("--route", default="5000", help="노선 검색어 (기본값: 5000)")
    args = parser.parse_args()

    api_key = os.getenv("GYEONGGI_BUS_API_KEY", "").strip()
    if not api_key:
        print(json.dumps({
            "ok": False,
            "reason": "GYEONGGI_BUS_API_KEY is not configured",
        }, ensure_ascii=False))
        return 2

    try:
        code, message, body, elapsed = _request(
            api_key,
            "busrouteservice",
            "getBusRouteList",
            {"keyword": args.route},
        )
        routes = _items(body.get("busRouteList"))
        route = _select_route(routes, args.route)
        route_id = _text(route.get("routeId"))
        _print_check(
            "route_list",
            elapsed=elapsed,
            result_code=code,
            result_message=message,
            route_count=len(routes),
            selected_route_id=route_id,
            selected_route_name=_text(route.get("routeName")),
            admin_name=_text(route.get("adminName")),
        )

        if not route_id:
            raise ApiCheckError("선택된 노선에 routeId가 없습니다.")

        code, message, body, elapsed = _request(
            api_key,
            "busrouteservice",
            "getBusRouteStationList",
            {"routeId": route_id},
        )
        stops = _items(body.get("busRouteStationList"))
        _print_check(
            "route_stations",
            elapsed=elapsed,
            result_code=code,
            result_message=message,
            stop_count=len(stops),
        )

        if not stops:
            raise ApiCheckError("노선 정류장 응답이 비어 있습니다.")

        first_stop = stops[0]
        station_id = _text(first_stop.get("stationId"))
        station_order = _text(first_stop.get("stationSeq"))
        if not station_id or not station_order:
            raise ApiCheckError("첫 정류장의 stationId 또는 stationSeq가 없습니다.")

        code, message, body, elapsed = _request(
            api_key,
            "busarrivalservice",
            "getBusArrivalItem",
            {
                "routeId": route_id,
                "stationId": station_id,
                "staOrder": station_order,
            },
        )
        arrivals = _items(body.get("busArrivalItem"))
        _print_check(
            "bus_arrival",
            elapsed=elapsed,
            result_code=code,
            result_message=message,
            station_id=station_id,
            station_order=station_order,
            arrival_count=len(arrivals),
        )

        code, message, body, elapsed = _request(
            api_key,
            "buslocationservice",
            "getBusLocationList",
            {"routeId": route_id},
        )
        locations = _items(body.get("busLocationList"))
        _print_check(
            "bus_locations",
            elapsed=elapsed,
            result_code=code,
            result_message=message,
            location_count=len(locations),
        )
    except ApiCheckError as exc:
        print(json.dumps({
            "ok": False,
            "error": str(exc),
        }, ensure_ascii=False))
        return 1

    print(json.dumps({
        "ok": True,
        "message": "경기도 버스 노선·정류장·도착·위치 API 호출이 완료되었습니다.",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
