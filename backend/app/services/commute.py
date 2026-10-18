from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import logging
import math
import re
from threading import Lock
from time import monotonic
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import os
import requests
load_dotenv()

logger = logging.getLogger(__name__)

from app.models.commute import CommuteProfile
from app.models.building import Building
from app.models.shuttle_map import (
    ShuttleMapRoute,
    ShuttleMapSchedule,
    ShuttleMapScheduleStop,
    ShuttleMapStop,
)
from app.models.user import User
from app.schemas.commute import (
    CommuteProfileCreate,
    CommuteProfileUpdate,
    CommuteSettingsUpdate,
    DisplayMode,
    CommuteDestinationResponse,
    CommuteTodayResponse,
    FirstClassResponse,
    LiveBusPositionResponse,
    LiveBusPositionsResponse,
    RouteSummaryResponse,
)
from app.services import timetable as timetable_services


class GeocodingError(Exception):
    pass


class TransitRouteError(Exception):
    pass


def _raise_tmap_geocoding_error(
    exc: requests.RequestException,
    operation: str,
) -> None:
    """TMAP 오류를 키를 노출하지 않는 진단 로그와 사용자 메시지로 변환한다."""
    response = exc.response
    status_code = response.status_code if response is not None else None
    response_text = response.text[:500] if response is not None else str(exc)
    logger.warning(
        "TMAP %s failed: status=%s response=%s",
        operation,
        status_code,
        response_text,
    )

    if status_code in {401, 403}:
        raise GeocodingError(
            "TMAP API 인증에 실패했습니다. 앱 키와 TMAP API 상품 권한을 확인해주세요."
        ) from exc
    if status_code == 429:
        raise GeocodingError(
            "TMAP API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
        ) from exc
    if status_code == 400:
        raise GeocodingError(
            "TMAP에서 주소를 찾지 못했거나 요청 형식이 올바르지 않습니다."
        ) from exc
    raise GeocodingError(f"TMAP {operation} 요청에 실패했습니다.") from exc

TMAP_API_KEY = os.getenv("TMAP_API_KEY")
TMAP_GEOCODING_URL = "https://apis.openapi.sk.com/tmap/geo/fullAddrGeo"
TMAP_POI_SEARCH_URL = "https://apis.openapi.sk.com/tmap/pois"

PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY")
TAGO_STOP_API_URL = (
    "https://apis.data.go.kr/1613000/BusSttnInfoInqireService/"
    "getCrdntPrxmtSttnList"
)
TAGO_ARRIVAL_API_URL = (
    "https://apis.data.go.kr/1613000/ArvlInfoInqireService/"
    "getSttnAcctoArvlPrearngeInfoList"
)
TAGO_BUS_LOCATION_API_URL = (
    "https://apis.data.go.kr/1613000/BusLcInfoInqireService/"
    "getRouteAcctoBusLcList"
)
TAGO_STOP_MATCH_MAX_DISTANCE_METERS = 150
TAGO_BUS_LOCATION_CACHE_TTL_SECONDS = 15
_tago_bus_location_cache: dict[
    tuple[str, str], tuple[float, LiveBusPositionsResponse]
] = {}
_tago_bus_location_cache_lock = Lock()


GOOGLE_MAPS_SERVER_API_KEY = (
    os.getenv("GOOGLE_MAPS_SERVER_API_KEY")
)

GOOGLE_MAPS_API_KEY = (
    os.getenv("GOOGLE_MAPS_API_KEY")
)
GOOGLE_ROUTES_API_URL = (
    "https://routes.googleapis.com/directions/v2:computeRoutes"
)
GOOGLE_ROUTES_FIELD_MASK = ",".join(
    [
        "routes.duration",
        "routes.distanceMeters",
        "routes.polyline.geoJsonLinestring",
        "routes.legs.steps.travelMode",
        "routes.legs.steps.staticDuration",
        "routes.legs.steps.distanceMeters",
        "routes.legs.steps.polyline.geoJsonLinestring",
        "routes.legs.steps.navigationInstruction",
        "routes.legs.steps.startLocation",
        "routes.legs.steps.endLocation",
        "routes.legs.steps.transitDetails",
    ]
)

SHUTTLE_ROUTE_NAME = "기흥역-이공관"
SHUTTLE_ORIGIN_STOP_NAME = "기흥역"
SHUTTLE_DESTINATION_STOP_NAME = "이공관"
SHUTTLE_BOARDING_BUFFER_MINUTES = 5

CAMPUS_DEFAULT_DESTINATION_NAME = "강남대학교"
CAMPUS_DEFAULT_LATITUDE = 37.2757
CAMPUS_DEFAULT_LONGITUDE = 127.1325

def get_commute_profile(db: Session, user: User) -> CommuteProfile | None:
    """현재 사용자의 통학 프로필을 조회한다."""
    return (
        db.query(CommuteProfile)
        .filter(CommuteProfile.user_id == user.id)
        .first()
    )


def create_commute_profile(
    db: Session,
    user: User,
    data: CommuteProfileCreate,
) -> CommuteProfile:
    """사용자의 통학 프로필을 생성한다."""

    if data.home_latitude is not None and data.home_longitude is not None:
        latitude = data.home_latitude
        longitude = data.home_longitude
    else:
        coordinates = geocode_address(data.home_address)
        latitude = coordinates["latitude"]
        longitude = coordinates["longitude"]

    profile = CommuteProfile(
        user_id=user.id,
        home_address=data.home_address,
        home_road_address=data.home_road_address,
        home_latitude=latitude,
        home_longitude=longitude,
        use_shuttle=data.use_shuttle,
        shuttle_destination="이공관",
        departure_buffer_minutes=data.departure_buffer_minutes,
    )

    try:
        db.add(profile)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(profile)
    return profile


def update_commute_profile(
    db: Session,
    user: User,
    data: CommuteProfileUpdate,
) -> CommuteProfile:
    """사용자의 주소와 통학 프로필을 수정한다."""
    profile = get_commute_profile(db, user)
    if profile is None:
        raise ValueError("Profile not found")

    update_data = data.model_dump(exclude_unset=True)

    has_selected_coordinates = (
        update_data.get("home_latitude") is not None
        and update_data.get("home_longitude") is not None
    )
    if not has_selected_coordinates:
        # 좌표는 반드시 한 쌍으로만 갱신한다. 일부만 전달되면 주소를 다시 지오코딩한다.
        update_data.pop("home_latitude", None)
        update_data.pop("home_longitude", None)
    if (
        "home_address" in update_data
        and update_data["home_address"] != profile.home_address
        and not has_selected_coordinates
    ):
        coordinates = geocode_address(update_data["home_address"])

        update_data["home_latitude"] = coordinates["latitude"]
        update_data["home_longitude"] = coordinates["longitude"]

        if coordinates.get("road_address"):
            update_data["home_road_address"] = coordinates["road_address"]

    for key, value in update_data.items():
        setattr(profile, key, value)

    

    try:
        db.commit()
        db.refresh(profile)
    except IntegrityError:
        db.rollback()
        raise

    return profile


def delete_commute_profile(db: Session, user: User) -> None:
    """사용자의 통학 프로필을 삭제한다."""
    profile = get_commute_profile(db, user)
    if profile is None:
        raise ValueError("Profile not found")

    db.delete(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise


def update_commute_setting(
    db: Session,
    user: User,
    data: CommuteSettingsUpdate,
) -> CommuteProfile:
    """셔틀 이용 여부와 출발 여유 시간을 수정한다."""
    profile = get_commute_profile(db, user)
    if profile is None:
        raise ValueError("Profile not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    try:
        db.commit()
        db.refresh(profile)
    except IntegrityError:
        db.rollback()
        raise

    return profile


def get_first_class(
    db: Session,
    user: User,
) -> FirstClassResponse | None:
    """메인 시간표 또는 최신 시간표에서 오늘의 첫 일정을 조회한다."""
    timetables = timetable_services.get_my_timetables(db, user)

    target_timetable = next(
        (timetable for timetable in timetables if timetable.is_main),
        None,
    )
    if target_timetable is None and timetables:
        # get_my_timetables가 최신순으로 정렬되어 있다는 전제의 fallback
        target_timetable = timetables[0]

    if target_timetable is None:
        return None

    timetable_detail = timetable_services.get_my_timetable_detail(
        db,
        user,
        target_timetable.id,
    )
    if timetable_detail is None:
        return None

    day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    today = day_names[datetime.now(ZoneInfo("Asia/Seoul")).weekday()]
    today_schedules: list[dict] = []

    for course in timetable_detail["courses"]:
        for schedule in course["schedules"]:
            if schedule.day_of_week != today:
                continue

            today_schedules.append(
                {
                    "course_id": course["id"],
                    "course_name": course["name"] or "이름 없는 강의",
                    "start_time": schedule.start_time,
                    "end_time": schedule.end_time,
                    "building_name": course.get("building_name"),
                    "room_name": course.get("room_name"),
                    "latitude": course.get("latitude"),
                    "longitude": course.get("longitude"),
                }
            )

    if not today_schedules:
        return None

    first_class = min(today_schedules, key=lambda item: item["start_time"])
    return FirstClassResponse(**first_class)


def get_today_commute(db: Session, user: User) -> CommuteTodayResponse:
    """오늘의 첫 정규 수업을 기준으로 통학 출발시간을 계산한다."""
    profile = get_commute_profile(db, user)
    if profile is None:
        return CommuteTodayResponse(
            status="setup_required",
            message="집 주소를 등록해주세요.",
        )

    first_class = get_first_class(db, user)
    display_mode = get_commute_display_mode(first_class)
    no_class_message = None

    if first_class is None:
        display_mode = "travel_time_only"
        no_class_message = "오늘 예정된 정규 수업이 없습니다."
        destination = CommuteDestinationResponse(
            destination_type="campus_gate",
            destination_name=CAMPUS_DEFAULT_DESTINATION_NAME,
            latitude=CAMPUS_DEFAULT_LATITUDE,
            longitude=CAMPUS_DEFAULT_LONGITUDE,
        )
    elif profile.use_shuttle:
        try:
            return _build_shuttle_commute_response(
                db=db,
                profile=profile,
                first_class=first_class,
                display_mode=display_mode,
            )
        except TransitRouteError:
            return CommuteTodayResponse(
                status="provider_error",
                display_mode=display_mode,
                first_class=first_class,
                message="셔틀 탑승 정류장까지의 대중교통 경로를 조회할 수 없습니다.",
            )
        except ValueError as exc:
            return CommuteTodayResponse(
                status="no_route",
                display_mode=display_mode,
                first_class=first_class,
                message=str(exc),
            )
    else:
        if first_class.latitude is None or first_class.longitude is None:
            return CommuteTodayResponse(
                status="no_route",
                display_mode=display_mode,
                first_class=first_class,
                message="첫 수업 건물의 위치 정보를 찾을 수 없습니다.",
            )

        destination = CommuteDestinationResponse(
            destination_type="building",
            destination_name=first_class.building_name or "첫 수업 건물",
            latitude=first_class.latitude,
            longitude=first_class.longitude,
        )

    timezone_info = ZoneInfo("Asia/Seoul")
    now = datetime.now(timezone_info)
    target_arrival = None
    if display_mode == "departure_recommendation":
        target_arrival = datetime.combine(
            now.date(),
            first_class.start_time,
            tzinfo=timezone_info,
        ) - timedelta(minutes=profile.departure_buffer_minutes)

    try:
        routes = get_transit_routes(
            start_latitude=profile.home_latitude,
            start_longitude=profile.home_longitude,
            end_latitude=destination.latitude,
            end_longitude=destination.longitude,
            arrival_time=target_arrival,
            departure_time=(
                now if display_mode == "travel_time_only" else None
            ),
        )
    except TransitRouteError:
        return CommuteTodayResponse(
            status="provider_error",
            display_mode=display_mode,
            first_class=first_class,
            destination=destination,
            message="대중교통 경로를 조회할 수 없습니다.",
        )

    if target_arrival is not None:
        routes = [
            route.model_copy(
                update={
                    "departure_time": (
                        target_arrival
                        - timedelta(minutes=route.duration_minutes)
                    ).time(),
                    "arrival_time": target_arrival.time(),
                    "buffer_minutes": profile.departure_buffer_minutes,
                }
            )
            for route in routes
        ]
    else:
        routes = [
            route.model_copy(
                update={
                    "departure_time": now.time(),
                    "arrival_time": (
                        now + timedelta(minutes=route.duration_minutes)
                    ).time(),
                    "buffer_minutes": profile.departure_buffer_minutes,
                }
            )
            for route in routes
        ]

    route, alternatives = _select_route_options(routes)

    return CommuteTodayResponse(
        status="ready",
        display_mode=display_mode,
        message=no_class_message,
        first_class=first_class,
        destination=destination,
        recommended_route=route,
        alternatives=alternatives,
        calculated_at=datetime.now(ZoneInfo("Asia/Seoul")),
    )


def _select_route_options(
    routes: list[RouteSummaryResponse],
) -> tuple[RouteSummaryResponse, list[RouteSummaryResponse]]:
    """Google 후보 경로를 사용자 선택 기준 네 가지로 구성한다."""
    google_recommended = routes[0].model_copy(
        update={
            "route_category": "google_recommended",
            "is_recommended": True,
        }
    )
    fastest = min(
        routes,
        key=lambda route: (
            route.duration_minutes,
            route.transfer_count,
            route.walking_minutes,
        ),
    ).model_copy(update={"route_category": "fastest", "is_recommended": False})
    least_walking = min(
        routes,
        key=lambda route: (
            route.walking_minutes,
            route.duration_minutes,
            route.transfer_count,
        ),
    ).model_copy(
        update={"route_category": "least_walking", "is_recommended": False}
    )
    fewest_transfers = min(
        routes,
        key=lambda route: (
            route.transfer_count,
            route.duration_minutes,
            route.walking_minutes,
        ),
    ).model_copy(
        update={"route_category": "fewest_transfers", "is_recommended": False}
    )

    return google_recommended, [fastest, least_walking, fewest_transfers]


def _build_shuttle_commute_response(
    db: Session,
    profile: CommuteProfile,
    first_class: FirstClassResponse,
    display_mode: DisplayMode | None,
) -> CommuteTodayResponse:
    """집에서 기흥역 셔틀 정류장까지 이동한 뒤 셔틀을 타는 경로를 계산한다."""
    route = (
        db.query(ShuttleMapRoute)
        .filter(
            ShuttleMapRoute.route_name == SHUTTLE_ROUTE_NAME,
            ShuttleMapRoute.is_active.is_(True),
        )
        .first()
    )
    if route is None:
        raise ValueError(f"셔틀 노선을 찾을 수 없습니다: {SHUTTLE_ROUTE_NAME}")

    schedule_rows = (
        db.query(ShuttleMapSchedule, ShuttleMapScheduleStop, ShuttleMapStop)
        .join(
            ShuttleMapScheduleStop,
            ShuttleMapScheduleStop.schedule_id == ShuttleMapSchedule.id,
        )
        .join(
            ShuttleMapStop,
            ShuttleMapStop.id == ShuttleMapScheduleStop.stop_id,
        )
        .filter(
            ShuttleMapSchedule.route_id == route.id,
            ShuttleMapSchedule.is_active.is_(True),
            ShuttleMapScheduleStop.stop_id.isnot(None),
        )
        .all()
    )

    schedules: dict[int, dict[str, object]] = {}
    for schedule, schedule_stop, stop in schedule_rows:
        item = schedules.setdefault(
            schedule.id,
            {
                "schedule": schedule,
                "stops": {},
            },
        )
        item["stops"][stop.stop_name] = schedule_stop

    today = datetime.now(ZoneInfo("Asia/Seoul"))
    day_of_week = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][
        today.weekday()
    ]

    origin_stop = None
    for item in schedules.values():
        stops = item["stops"]
        candidate = stops.get(SHUTTLE_ORIGIN_STOP_NAME)
        if candidate is not None:
            origin_stop = candidate.stop
            break

    if origin_stop is None:
        raise ValueError(f"셔틀 탑승 정류장을 찾을 수 없습니다: {SHUTTLE_ORIGIN_STOP_NAME}")

    destination = CommuteDestinationResponse(
        destination_type="shuttle_stop",
        destination_name=SHUTTLE_ORIGIN_STOP_NAME,
        latitude=origin_stop.latitude,
        longitude=origin_stop.longitude,
    )

    try:
        transit_route = get_transit_route(
            start_latitude=profile.home_latitude,
            start_longitude=profile.home_longitude,
            end_latitude=origin_stop.latitude,
            end_longitude=origin_stop.longitude,
            departure_time=today,
        )
    except TransitRouteError:
        return CommuteTodayResponse(
            status="provider_error",
            display_mode=display_mode,
            first_class=first_class,
            destination=destination,
            message="셔틀 정류장까지의 대중교통 경로를 조회할 수 없습니다.",
        )

    target_arrival = None
    if display_mode == "departure_recommendation":
        target_arrival = datetime.combine(
            today.date(),
            first_class.start_time,
            tzinfo=today.tzinfo,
        ) - timedelta(minutes=profile.departure_buffer_minutes)

    candidates: list[dict[str, object]] = []
    for item in schedules.values():
        schedule = item["schedule"]
        if schedule.day_of_week != day_of_week:
            continue

        stops = item["stops"]
        origin_schedule_stop = stops.get(SHUTTLE_ORIGIN_STOP_NAME)
        destination_schedule_stop = stops.get(SHUTTLE_DESTINATION_STOP_NAME)
        if origin_schedule_stop is None or destination_schedule_stop is None:
            continue

        origin_datetime = datetime.combine(
            today.date(),
            origin_schedule_stop.arrival_time,
            tzinfo=today.tzinfo,
        )
        destination_datetime = datetime.combine(
            today.date(),
            destination_schedule_stop.arrival_time,
            tzinfo=today.tzinfo,
        )

        recommended_departure = origin_datetime - timedelta(
            minutes=(
                transit_route.duration_minutes + SHUTTLE_BOARDING_BUFFER_MINUTES
            )
        )

        if recommended_departure < today:
            continue
        if target_arrival is not None and destination_datetime > target_arrival:
            continue

        candidates.append(
            {
                "origin_datetime": origin_datetime,
                "destination_datetime": destination_datetime,
                "recommended_departure": recommended_departure,
            }
        )

    if not candidates:
        raise ValueError("오늘 이용 가능한 셔틀 시간표를 찾을 수 없습니다.")

    if display_mode == "departure_recommendation":
        selected = max(candidates, key=lambda item: item["origin_datetime"])
    else:
        selected = min(candidates, key=lambda item: item["origin_datetime"])

    origin_datetime = selected["origin_datetime"]
    destination_datetime = selected["destination_datetime"]
    recommended_departure = selected["recommended_departure"]
    shuttle_duration = max(
        1,
        math.ceil((destination_datetime - origin_datetime).total_seconds() / 60),
    )

    total_duration = (
        transit_route.duration_minutes
        + SHUTTLE_BOARDING_BUFFER_MINUTES
        + shuttle_duration
    )

    shuttle_route = RouteSummaryResponse(
        transport_type="shuttle",
        route_name=f"집 → {SHUTTLE_ORIGIN_STOP_NAME} → {SHUTTLE_DESTINATION_STOP_NAME}",
        departure_time=(
            recommended_departure.time()
            if display_mode == "departure_recommendation"
            else None
        ),
        arrival_time=(
            destination_datetime.time()
            if display_mode == "departure_recommendation"
            else None
        ),
        duration_minutes=total_duration,
        walking_minutes=transit_route.walking_minutes,
        transfer_count=transit_route.transfer_count,
        buffer_minutes=profile.departure_buffer_minutes,
        boarding_stop_name=SHUTTLE_ORIGIN_STOP_NAME,
        shuttle_departure_time=origin_datetime.time(),
        shuttle_arrival_time=destination_datetime.time(),
        route_path=transit_route.route_path,
        route_steps=transit_route.route_steps,
        is_recommended=True,
        recommendation_reason=(
            f"{SHUTTLE_ORIGIN_STOP_NAME} 셔틀 출발 "
            f"{origin_datetime.strftime('%H:%M')} 기준"
        ),
    )

    return CommuteTodayResponse(
        status="ready",
        display_mode=display_mode,
        first_class=first_class,
        destination=destination,
        recommended_route=shuttle_route,
        calculated_at=today,
    )


def get_commute_display_mode(
    first_class: FirstClassResponse | None,
    now: datetime | None = None,
) -> DisplayMode | None:
    """첫 수업 전후의 홈 카드 표시 모드를 결정한다."""
    if first_class is None:
        return None

    current_time = now or datetime.now(ZoneInfo("Asia/Seoul"))
    return (
        "departure_recommendation"
        if current_time.time() < first_class.start_time
        else "travel_time_only"
    )


def _tago_request_params(**params: object) -> dict[str, object]:
    """requests가 인증키를 한 번만 URL 인코딩하도록 요청 파라미터를 만든다."""
    return {
        "serviceKey": unquote(PUBLIC_API_KEY or ""),
        "_type": "json",
        **params,
    }


def _get_tago_items(data: dict) -> list[dict]:
    """TAGO의 단일 객체/배열 응답을 항상 배열로 정규화한다."""
    response = data.get("response", {})
    header = response.get("header", {})
    result_code = str(header.get("resultCode", ""))
    if result_code not in {"0", "00"}:
        raise TransitRouteError(
            header.get("resultMsg") or "TAGO API 요청에 실패했습니다."
        )

    items = response.get("body", {}).get("items", {})
    if not items:
        return []

    item = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(item, dict):
        return [item]
    return item if isinstance(item, list) else []


def _normalize_stop_name(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[\s.·()\[\]-]", "", name).replace("정류장", "").lower()


def _normalize_route_number(route_name: str | None) -> str:
    if not route_name:
        return ""
    route_number = route_name.rsplit(":", 1)[-1]
    return re.sub(r"[^0-9A-Za-z가-힣]", "", route_number).upper()


def _distance_meters(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """두 WGS84 좌표 사이의 직선거리를 Haversine 공식으로 계산한다."""
    earth_radius = 6_371_000
    lat1 = math.radians(latitude1)
    lat2 = math.radians(latitude2)
    delta_lat = math.radians(latitude2 - latitude1)
    delta_lon = math.radians(longitude2 - longitude1)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def resolve_tago_stop(
    latitude: float,
    longitude: float,
    stop_name: str | None = None,
) -> dict | None:
    """외부 경로의 정류장 좌표를 TAGO의 cityCode/nodeId로 매핑한다."""
    if not PUBLIC_API_KEY:
        return None

    try:
        response = requests.get(
            TAGO_STOP_API_URL,
            params=_tago_request_params(
                gpsLati=latitude,
                gpsLong=longitude,
                numOfRows=30,
                pageNo=1,
            ),
            headers={"Accept": "application/json"},
            timeout=5,
        )
        response.raise_for_status()
        candidates = _get_tago_items(response.json())
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise TransitRouteError("TAGO 정류장 조회에 실패했습니다.") from exc

    normalized_target_name = _normalize_stop_name(stop_name)
    matched_candidates: list[dict] = []

    for candidate in candidates:
        try:
            candidate_latitude = float(candidate["gpslati"])
            candidate_longitude = float(candidate["gpslong"])
            node_id = str(candidate["nodeid"])
            city_code = str(candidate["citycode"])
        except (KeyError, TypeError, ValueError):
            continue

        distance = _distance_meters(
            latitude,
            longitude,
            candidate_latitude,
            candidate_longitude,
        )
        if distance > TAGO_STOP_MATCH_MAX_DISTANCE_METERS:
            continue

        candidate_name = str(candidate.get("nodenm") or "")
        normalized_candidate_name = _normalize_stop_name(candidate_name)
        name_matches = bool(
            normalized_target_name
            and normalized_candidate_name
            and (
                normalized_target_name == normalized_candidate_name
                or normalized_target_name in normalized_candidate_name
                or normalized_candidate_name in normalized_target_name
            )
        )
        matched_candidates.append(
            {
                "node_id": node_id,
                "city_code": city_code,
                "stop_name": candidate_name,
                "latitude": candidate_latitude,
                "longitude": candidate_longitude,
                "distance_meters": round(distance, 1),
                "name_matches": name_matches,
            }
        )

    if not matched_candidates:
        return None

    # 이름이 같은 정류장을 우선하고, 같은 이름의 맞은편 정류장은 거리로 구분한다.
    matched_candidates.sort(
        key=lambda item: (not item["name_matches"], item["distance_meters"])
    )
    best_match = matched_candidates[0]

    # 이름이 다르면 좌표가 매우 가까운 경우에만 자동 매핑한다.
    if not best_match["name_matches"] and best_match["distance_meters"] > 50:
        return None
    return best_match


def _get_tago_bus_arrival(
    city_code: str,
    node_id: str,
    route_name: str | None,
) -> dict | None:
    """TAGO 정류장의 실시간 도착정보 중 추천 노선과 일치하는 버스를 찾는다."""
    if not PUBLIC_API_KEY:
        return None

    try:
        response = requests.get(
            TAGO_ARRIVAL_API_URL,
            params=_tago_request_params(
                cityCode=city_code,
                nodeId=node_id,
                numOfRows=100,
                pageNo=1,
            ),
            headers={"Accept": "application/json"},
            timeout=5,
        )
        response.raise_for_status()
        arrivals = _get_tago_items(response.json())
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise TransitRouteError("TAGO 버스 도착정보 조회에 실패했습니다.") from exc

    target_route_number = _normalize_route_number(route_name)
    matching_arrivals: list[dict] = []
    for arrival in arrivals:
        if (
            target_route_number
            and _normalize_route_number(str(arrival.get("routeno") or ""))
            != target_route_number
        ):
            continue
        try:
            arrival_seconds = max(0, int(arrival["arrtime"]))
            remaining_stops = max(0, int(arrival.get("arrprevstationcnt") or 0))
        except (KeyError, TypeError, ValueError):
            continue
        matching_arrivals.append(
            {
                "route_number": str(arrival.get("routeno") or ""),
                "route_id": str(arrival.get("routeid") or ""),
                "arrival_seconds": arrival_seconds,
                "arrival_minutes": math.ceil(arrival_seconds / 60),
                "remaining_stops": remaining_stops,
            }
        )

    if not matching_arrivals:
        return None
    return min(matching_arrivals, key=lambda item: item["arrival_seconds"])


def get_live_bus_positions(
    city_code: str,
    route_id: str,
) -> LiveBusPositionsResponse:
    """TAGO 노선별 실시간 차량 위치를 15초 동안 프로세스 내 캐시한다."""
    if not PUBLIC_API_KEY:
        raise TransitRouteError("TAGO API 키가 설정되지 않았습니다.")

    cache_key = (city_code, route_id)
    current_monotonic = monotonic()
    with _tago_bus_location_cache_lock:
        cached = _tago_bus_location_cache.get(cache_key)
        if cached and cached[0] > current_monotonic:
            return cached[1]

    try:
        response = requests.get(
            TAGO_BUS_LOCATION_API_URL,
            params=_tago_request_params(
                cityCode=city_code,
                routeId=route_id,
                numOfRows=100,
                pageNo=1,
            ),
            headers={"Accept": "application/json"},
            timeout=5,
        )
        response.raise_for_status()
        items = _get_tago_items(response.json())
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise TransitRouteError("TAGO 버스 위치정보 조회에 실패했습니다.") from exc

    vehicles: list[LiveBusPositionResponse] = []
    for item in items:
        try:
            latitude = float(item["gpslati"])
            longitude = float(item["gpslong"])
        except (KeyError, TypeError, ValueError):
            continue

        try:
            current_stop_order = int(item["nodeord"])
        except (KeyError, TypeError, ValueError):
            current_stop_order = None

        vehicle_number = str(item.get("vehicleno") or "").strip()
        if not vehicle_number:
            continue

        vehicles.append(
            LiveBusPositionResponse(
                vehicle_number=vehicle_number,
                route_name=str(item.get("routenm") or "").strip() or None,
                latitude=latitude,
                longitude=longitude,
                current_stop_order=current_stop_order,
                current_stop_id=str(item.get("nodeid") or "").strip() or None,
                current_stop_name=str(item.get("nodenm") or "").strip() or None,
            )
        )

    result = LiveBusPositionsResponse(
        city_code=city_code,
        route_id=route_id,
        cached_at=datetime.now(timezone.utc),
        cache_ttl_seconds=TAGO_BUS_LOCATION_CACHE_TTL_SECONDS,
        vehicles=vehicles,
    )
    with _tago_bus_location_cache_lock:
        expired_keys = [
            key
            for key, (expires_at, _) in _tago_bus_location_cache.items()
            if expires_at <= current_monotonic
        ]
        for key in expired_keys:
            _tago_bus_location_cache.pop(key, None)
        _tago_bus_location_cache[cache_key] = (
            current_monotonic + TAGO_BUS_LOCATION_CACHE_TTL_SECONDS,
            result,
        )

    return result


def get_transit_routes(
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    departure_time: datetime | None = None,
    arrival_time: datetime | None = None,
) -> list[RouteSummaryResponse]:
    """Google 추천·대체 대중교통 경로를 조회하고 TAGO 정보로 보강한다."""
    if not GOOGLE_MAPS_SERVER_API_KEY:
        raise TransitRouteError("Google Maps 서버 API 키가 설정되지 않았습니다.")

    if departure_time is not None and arrival_time is not None:
        raise ValueError(
            "departure_time과 arrival_time은 동시에 지정할 수 없습니다"
        )

    request_body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": start_latitude,
                    "longitude": start_longitude,
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": end_latitude,
                    "longitude": end_longitude,
                }
            }
        },
        "travelMode": "TRANSIT",
        "computeAlternativeRoutes": True,
        "languageCode": "ko",
        "units": "METRIC",
        "polylineEncoding": "GEO_JSON_LINESTRING",
        "polylineQuality": "HIGH_QUALITY",
    }

    if arrival_time is not None:
        request_body["arrivalTime"] = _to_google_timestamp(arrival_time)
    elif departure_time is not None:
        request_body["departureTime"] = _to_google_timestamp(departure_time)

    try:
        response = requests.post(
            GOOGLE_ROUTES_API_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_MAPS_SERVER_API_KEY,
                "X-Goog-FieldMask": GOOGLE_ROUTES_FIELD_MASK,
            },
            json=request_body,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning(
            "Google Routes request failed: status=%s response=%s",
            exc.response.status_code if exc.response is not None else None,
            exc.response.text[:500] if exc.response is not None else str(exc),
        )
        raise TransitRouteError("Google 대중교통 경로 요청에 실패했습니다.") from exc
    except ValueError as exc:
        raise TransitRouteError("Google 대중교통 응답을 해석할 수 없습니다.") from exc

    routes = data.get("routes", [])
    if not routes:
        raise TransitRouteError("이용 가능한 대중교통 경로를 찾을 수 없습니다.")

    return [_parse_google_transit_route(route) for route in routes]


def get_transit_route(
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    departure_time: datetime | None = None,
    arrival_time: datetime | None = None,
) -> RouteSummaryResponse:
    """기존 호출부를 위해 Google의 첫 번째 추천 경로만 반환한다."""
    return get_transit_routes(
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        end_latitude=end_latitude,
        end_longitude=end_longitude,
        departure_time=departure_time,
        arrival_time=arrival_time,
    )[0]


def _parse_google_transit_route(route: dict) -> RouteSummaryResponse:
    """Google 경로 한 개를 앱의 공통 대중교통 응답 모델로 변환한다."""

    steps = [
        step for leg in route.get("legs", []) for step in leg.get("steps", [])
    ]

    transit_steps = [
        step for step in steps if step.get("travelMode") == "TRANSIT"
    ]

    walking_minutes = sum(
        _google_duration_minutes(step.get("staticDuration"))
        for step in steps
        if step.get("travelMode") == "WALK"
    )

    route_names: list[str] = []
    vehicle_types: set[str] = set()

    for step in transit_steps:
        transit_details = step.get("transitDetails", {})
        transit_line = transit_details.get("transitLine", {})

        route_name = (
            transit_line.get("nameShort") or transit_line.get("name")
        )
        if route_name and route_name not in route_names:
            route_names.append(route_name)

        vehicle_type = transit_line.get("vehicle", {}).get("type")
        if vehicle_type:
            vehicle_types.add(vehicle_type)

    if not transit_steps:
        transport_type = "walking"
    elif vehicle_types and all(
        "BUS" in vehicle_type for vehicle_type in vehicle_types
    ):
        transport_type = "bus"
    elif vehicle_types == {"SUBWAY"}:
        transport_type = "subway"
    else:
        transport_type = "mixed"

    boarding_stop_name = None
    bus_arrival_minutes = None
    bus_remaining_stops = None
    recommendation_reason = "Google Maps 추천 경로"
    first_bus_live_context: dict[str, str] = {}

    if transit_steps:
        first_transit_details = transit_steps[0].get("transitDetails", {})
        first_transit_line = first_transit_details.get("transitLine", {})
        departure_stop = (
            first_transit_details.get("stopDetails", {}).get("departureStop", {})
        )
        boarding_stop_name = departure_stop.get("name")

        first_vehicle_type = str(
            first_transit_line.get("vehicle", {}).get("type") or ""
        )
        if "BUS" in first_vehicle_type:
            stop_location = departure_stop.get("location", {}).get("latLng", {})
            try:
                tago_stop = resolve_tago_stop(
                    latitude=float(stop_location["latitude"]),
                    longitude=float(stop_location["longitude"]),
                    stop_name=boarding_stop_name,
                )
                if tago_stop:
                    arrival = _get_tago_bus_arrival(
                        city_code=tago_stop["city_code"],
                        node_id=tago_stop["node_id"],
                        route_name=(
                            first_transit_line.get("nameShort")
                            or first_transit_line.get("name")
                        ),
                    )
                    if arrival:
                        bus_arrival_minutes = arrival["arrival_minutes"]
                        bus_remaining_stops = arrival["remaining_stops"]
                        first_bus_live_context = {
                            "tago_city_code": tago_stop["city_code"],
                            "tago_route_id": arrival["route_id"],
                            "tago_boarding_stop_id": tago_stop["node_id"],
                        }
                        recommendation_reason = (
                            "Google Maps 추천 경로 · "
                            f"{arrival['route_number']}번 버스 "
                            f"약 {bus_arrival_minutes}분 후 도착"
                        )
            except (TransitRouteError, KeyError, TypeError, ValueError):
                # TAGO 보강 정보가 실패해도 Google 경로 자체는 반환한다.
                logger.info("TAGO 버스 도착정보 보강에 실패했습니다.", exc_info=True)

    duration_minutes = max(
        1,
        _google_duration_minutes(route.get("duration")),
    )

    transfer_count = max(0, len(transit_steps) - 1)

    # 전체 경로: Google GeoJSON [longitude, latitude]를 Expo Maps 좌표로 변환한다.
    geo_json = (
        route.get("polyline", {})
        .get("geoJsonLinestring", {})
    )

    coordinates = geo_json.get("coordinates", [])

    route_path = [
        {
            "latitude": latitude,
            "longitude": longitude,
        }
        for longitude, latitude in coordinates
    ]

    # 단계별 경로: 도보와 대중교통을 지도에서 다른 색으로 표시할 수 있게 반환한다.
    route_steps: list[dict] = []
    for step in steps:
        step_coordinates = (
            step.get("polyline", {})
            .get("geoJsonLinestring", {})
            .get("coordinates", [])
        )
        transit_details = step.get("transitDetails", {})
        transit_line = transit_details.get("transitLine", {})
        stop_details = transit_details.get("stopDetails", {})
        live_context = (
            first_bus_live_context
            if transit_steps and step is transit_steps[0]
            else {}
        )

        route_steps.append(
            {
                "travel_mode": step.get("travelMode", "UNKNOWN"),
                "duration_minutes": _google_duration_minutes(
                    step.get("staticDuration")
                ),
                "distance_meters": step.get("distanceMeters", 0),
                "instruction": step.get("navigationInstruction", {}).get(
                    "instructions"
                ),
                "transit_line_name": (
                    transit_line.get("nameShort") or transit_line.get("name")
                ),
                "transit_line_color": transit_line.get("color"),
                "vehicle_type": transit_line.get("vehicle", {}).get("type"),
                "departure_stop_name": stop_details.get(
                    "departureStop", {}
                ).get("name"),
                "arrival_stop_name": stop_details.get("arrivalStop", {}).get(
                    "name"
                ),
                **live_context,
                "route_path": [
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                    for longitude, latitude in step_coordinates
                ],
            }
        )

    return RouteSummaryResponse(
        transport_type=transport_type,
        route_name=" / ".join(route_names) if route_names else None,
        duration_minutes=duration_minutes,
        walking_minutes=walking_minutes,
        transfer_count=transfer_count,
        route_path=route_path,
        route_steps=route_steps,
        boarding_stop_name=boarding_stop_name,
        bus_arrival_minutes=bus_arrival_minutes,
        bus_remaining_stops=bus_remaining_stops,
        is_recommended=True,
        recommendation_reason=recommendation_reason,
    )


def geocode_address(address: str) -> dict:
    if not TMAP_API_KEY:
        raise GeocodingError("TMAP_API_KEY가 설정되지 않았습니다.")

    params = {
        "version": 1,
        "addressFlag": "F00",
        "coordType": "WGS84GEO",
        "fullAddr": address,
        "page": 1,
        "count": 20,
    }
    try:
        response = requests.get(
            TMAP_GEOCODING_URL,
            params=params,
            headers={
                "Accept": "application/json",
                "appKey": TMAP_API_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        _raise_tmap_geocoding_error(exc, "지오코딩")
    except ValueError as exc:
        raise GeocodingError("TMAP 응답을 해석할 수 없습니다.") from exc

    coordinate_info = data.get("coordinateInfo", {})
    coordinates = coordinate_info.get("coordinate", [])

    if not coordinates:
        raise GeocodingError("주소에 해당하는 좌표를 찾을 수 없습니다.")

    result = coordinates[0]

    latitude = result.get("latEntr") or result.get("lat")
    longitude = result.get("lonEntr") or result.get("lon")

    if not latitude or not longitude:
        raise GeocodingError("TMAP 응답에 좌표 정보가 없습니다.")

    return {
        "address": address,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "match_flag": result.get("matchFlag"),
        "road_address": result.get("newRoadName"),
        "building_name": result.get("newBuildingName"),
    }


def search_addresses(query: str, limit: int = 10) -> list[dict]:
    """TMAP POI 통합검색 결과를 통학 주소 선택용 목록으로 반환한다."""
    if not TMAP_API_KEY:
        raise GeocodingError("TMAP_API_KEY가 설정되지 않았습니다.")

    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return []

    try:
        response = requests.get(
            TMAP_POI_SEARCH_URL,
            params={
                "version": 1,
                "searchKeyword": normalized_query,
                "searchType": "all",
                "searchtypCd": "A",
                "page": 1,
                "count": max(1, min(limit, 20)),
                "reqCoordType": "WGS84GEO",
                "resCoordType": "WGS84GEO",
                "multiPoint": "N",
                "poiGroupYn": "N",
            },
            headers={
                "Accept": "application/json",
                "appKey": TMAP_API_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        _raise_tmap_geocoding_error(exc, "POI 통합검색")
    except ValueError as exc:
        raise GeocodingError("TMAP POI 검색 응답을 해석할 수 없습니다.") from exc

    pois = data.get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
    if isinstance(pois, dict):
        pois = [pois]
    if not isinstance(pois, list):
        pois = []

    results: list[dict] = []
    seen: set[tuple[str, float, float]] = set()

    for item in pois:
        if not isinstance(item, dict):
            continue

        latitude = item.get("frontLat") or item.get("noorLat")
        longitude = item.get("frontLon") or item.get("noorLon")
        if latitude is None or longitude is None:
            continue

        try:
            latitude_value = float(latitude)
            longitude_value = float(longitude)
        except (TypeError, ValueError):
            continue

        region_parts = [
            str(item.get(key) or "").strip()
            for key in ("upperAddrName", "middleAddrName")
            if item.get(key)
        ]
        lot_address = " ".join(
            part
            for part in (
                *region_parts,
                str(item.get("lowerAddrName") or "").strip(),
                str(item.get("detailAddrName") or "").strip(),
            )
            if part
        )

        road_address = _get_poi_road_address(item, region_parts)
        building_name = str(item.get("name") or "").strip() or None
        address = road_address or lot_address or building_name or normalized_query
        key = (address, latitude_value, longitude_value)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "address": address,
                "road_address": road_address or None,
                "building_name": building_name,
                "latitude": latitude_value,
                "longitude": longitude_value,
            }
        )

    # POI 검색이 놓치는 완전한 도로명/지번 주소는 Full Text Geocoding으로 보완한다.
    if not results:
        try:
            coordinate = geocode_address(normalized_query)
        except GeocodingError as exc:
            if "좌표를 찾을 수 없습니다" in str(exc):
                return []
            raise
        results.append(
            {
                "address": coordinate.get("road_address") or normalized_query,
                "road_address": coordinate.get("road_address"),
                "building_name": coordinate.get("building_name"),
                "latitude": coordinate["latitude"],
                "longitude": coordinate["longitude"],
            }
        )

    return results


def _get_poi_road_address(item: dict, region_parts: list[str]) -> str:
    """TMAP POI 응답의 여러 도로명 주소 형식을 하나의 문자열로 정규화한다."""
    new_address_list = item.get("newAddressList") or {}
    if isinstance(new_address_list, dict):
        new_addresses = new_address_list.get("newAddress") or []
    else:
        new_addresses = new_address_list
    if isinstance(new_addresses, dict):
        new_addresses = [new_addresses]
    if not isinstance(new_addresses, list):
        new_addresses = []

    for new_address in new_addresses:
        if not isinstance(new_address, dict):
            continue
        full_address = str(new_address.get("fullAddressRoad") or "").strip()
        if full_address:
            return full_address

    road_name = str(item.get("roadName") or "").strip()
    building_number = str(item.get("firstBuildNo") or "").strip()
    second_building_number = str(item.get("secondBuildNo") or "").strip()
    if building_number and second_building_number and second_building_number != "0":
        building_number = f"{building_number}-{second_building_number}"

    return " ".join(
        part for part in (*region_parts, road_name, building_number) if part
    )


def _to_google_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("Asia/Seoul"))

    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _google_duration_seconds(value: str | None) -> float:
    """Google Duration 변환(Seconds)"""
    if not value or not value.endswith("s"):
        return 0

    try:
        return float(value[:-1])
    except ValueError:
        return 0


def _google_duration_minutes(value: str | None) -> int:
    """Google Duration 변환(Minutes)"""
    seconds = _google_duration_seconds(value)
    return math.ceil(seconds / 60)
