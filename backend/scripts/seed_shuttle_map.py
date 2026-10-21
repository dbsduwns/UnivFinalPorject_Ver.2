"""shuttle_map_seed.json을 셔틀 길찾기 테이블에 반영합니다."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SEED_PATH = BACKEND_DIR / "data" / "shuttle_map_seed.json"
sys.path.insert(0, str(BACKEND_DIR))


def configure_database_url_from_cli() -> None:
    """app.database를 가져오기 전에 선택한 DB URL을 적용한다.

    기본값은 환경변수 DATABASE_URL이다. 운영 DB를 명시적으로 지정해야 할 때만
    --database-url을 사용하며, URL 자체는 어느 로그에도 출력하지 않는다.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--database-url")
    arguments, _ = parser.parse_known_args()
    if arguments.database_url:
        os.environ["DATABASE_URL"] = arguments.database_url


configure_database_url_from_cli()

from app.database import SessionLocal  # noqa: E402
from app.models.shuttle_map import (  # noqa: E402
    ShuttleMapRoute,
    ShuttleMapSchedule,
    ShuttleMapScheduleStop,
    ShuttleMapStop,
)


def parse_time(value: str) -> time:
    """HH:MM 형식의 문자열을 SQLAlchemy Time 값으로 변환합니다."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"잘못된 시간 형식입니다: {value!r} (HH:MM 필요)") from exc


def load_seed_data(seed_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"seed 파일을 찾을 수 없습니다: {seed_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 형식이 올바르지 않습니다: {exc}") from exc

    routes = payload.get("routes")
    if not isinstance(routes, list):
        raise ValueError("seed JSON의 routes는 배열이어야 합니다.")
    return payload


def get_or_create_route(db, route_data: dict[str, Any]) -> ShuttleMapRoute:
    route_name = str(route_data.get("route_name") or "").strip()
    if not route_name:
        raise ValueError("route_name이 비어 있습니다.")

    route = (
        db.query(ShuttleMapRoute)
        .filter(ShuttleMapRoute.route_name == route_name)
        .one_or_none()
    )
    if route is None:
        route = ShuttleMapRoute(route_name=route_name, is_active=True)
        db.add(route)
        db.flush()

    route.is_active = True
    return route


def get_or_create_stop(db, stop_data: dict[str, Any]) -> ShuttleMapStop:
    stop_name = str(stop_data.get("stop_name") or "").strip()
    latitude = stop_data.get("latitude")
    longitude = stop_data.get("longitude")

    if not stop_name:
        raise ValueError("stop_name이 비어 있습니다.")
    if latitude is None or longitude is None:
        raise ValueError(f"정류장 좌표가 없습니다: {stop_name}")

    stop = (
        db.query(ShuttleMapStop)
        .filter(
            ShuttleMapStop.stop_name == stop_name,
            ShuttleMapStop.latitude == float(latitude),
            ShuttleMapStop.longitude == float(longitude),
        )
        .one_or_none()
    )
    if stop is None:
        stop = ShuttleMapStop(
            stop_name=stop_name,
            latitude=float(latitude),
            longitude=float(longitude),
        )
        db.add(stop)
        db.flush()
    return stop


def build_arrival_time(departure_time: time, elapsed_minutes: int) -> time:
    base = datetime.combine(datetime.min.date(), departure_time)
    return (base + timedelta(minutes=elapsed_minutes)).time()


def replace_schedule_stops(
    db,
    schedule: ShuttleMapSchedule,
    stops: list[dict[str, Any]],
    stop_by_order: dict[int, ShuttleMapStop],
) -> None:
    db.query(ShuttleMapScheduleStop).filter(
        ShuttleMapScheduleStop.schedule_id == schedule.id
    ).delete(synchronize_session=False)
    db.flush()

    elapsed_minutes = 0
    for stop_data in sorted(stops, key=lambda item: int(item["stop_order"])):
        stop_order = int(stop_data["stop_order"])
        if stop_order not in stop_by_order:
            raise ValueError(f"정류장 순서를 찾을 수 없습니다: {stop_order}")

        if stop_order != 1:
            segment_minutes = int(stop_data.get("travel_minutes_from_previous", 0))
            if segment_minutes < 0:
                raise ValueError("travel_minutes_from_previous는 음수일 수 없습니다.")
            elapsed_minutes += segment_minutes

        db.add(
            ShuttleMapScheduleStop(
                schedule_id=schedule.id,
                stop_id=stop_by_order[stop_order].id,
                arrival_time=build_arrival_time(
                    schedule.departure_time,
                    elapsed_minutes,
                ),
                stop_order=stop_order,
            )
        )


def upsert_route(db, route_data: dict[str, Any]) -> tuple[int, int]:
    route = get_or_create_route(db, route_data)
    stops = route_data.get("stops")
    schedules = route_data.get("schedules")

    if not isinstance(stops, list) or not stops:
        raise ValueError(f"정류장이 없는 노선입니다: {route.route_name}")
    if not isinstance(schedules, list):
        raise ValueError(f"schedules가 배열이 아닙니다: {route.route_name}")

    orders = [int(stop["stop_order"]) for stop in stops]
    if len(orders) != len(set(orders)):
        raise ValueError(f"정류장 순서가 중복됩니다: {route.route_name}")

    stop_by_order = {
        int(stop_data["stop_order"]): get_or_create_stop(db, stop_data)
        for stop_data in stops
    }

    schedule_count = 0
    for schedule_data in schedules:
        day_of_week = str(schedule_data.get("day_of_week") or "").upper()
        if len(day_of_week) != 3:
            raise ValueError(f"요일 형식이 올바르지 않습니다: {day_of_week!r}")

        departure_times = schedule_data.get("departure_times")
        if not isinstance(departure_times, list):
            raise ValueError(
                f"departure_times가 배열이 아닙니다: {route.route_name}/{day_of_week}"
            )

        for departure_value in departure_times:
            departure_time = parse_time(str(departure_value))
            schedule = (
                db.query(ShuttleMapSchedule)
                .filter(
                    ShuttleMapSchedule.route_id == route.id,
                    ShuttleMapSchedule.day_of_week == day_of_week,
                    ShuttleMapSchedule.departure_time == departure_time,
                )
                .one_or_none()
            )
            if schedule is None:
                schedule = ShuttleMapSchedule(
                    route_id=route.id,
                    day_of_week=day_of_week,
                    departure_time=departure_time,
                    is_active=True,
                )
                db.add(schedule)
                db.flush()
            else:
                schedule.is_active = True

            replace_schedule_stops(db, schedule, stops, stop_by_order)
            schedule_count += 1

    return len(stop_by_order), schedule_count


def seed_shuttle_map(seed_path: Path) -> None:
    payload = load_seed_data(seed_path)
    db = SessionLocal()
    total_stops = 0
    total_schedules = 0

    try:
        database_url = os.environ.get("DATABASE_URL", "")
        parsed_url = urlparse(database_url)
        database_target = (
            f"{parsed_url.scheme}://{parsed_url.hostname or 'unknown'}"
            f"/{parsed_url.path.lstrip('/') or 'unknown'}"
        )
        print(f"DB 적재 대상: {database_target}")

        for route_data in payload["routes"]:
            stops, schedules = upsert_route(db, route_data)
            total_stops += stops
            total_schedules += schedules
            print(
                f"[OK] {route_data['route_name']}: "
                f"정류장 {stops}개, 일정 {schedules}개 반영"
            )

        db.commit()
        saved_route_count = db.query(ShuttleMapRoute).count()
        saved_schedule_count = db.query(ShuttleMapSchedule).count()
        saved_stop_count = db.query(ShuttleMapStop).count()
        print(
            f"\n셔틀맵 seed 완료: 노선 {len(payload['routes'])}개, "
            f"정류장 {total_stops}개, 일정 {total_schedules}개"
        )
        print(
            "DB 저장 확인: "
            f"노선 {saved_route_count}개, 일정 {saved_schedule_count}개, "
            f"정류장 {saved_stop_count}개"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="shuttle_map_seed.json을 PostgreSQL에 저장합니다."
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help="셔틀맵 seed JSON 경로",
    )
    parser.add_argument(
        "--database-url",
        help="기본 DATABASE_URL 대신 사용할 PostgreSQL URL. 출력에는 비밀값을 포함하지 않습니다.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_shuttle_map(args.seed_path)
