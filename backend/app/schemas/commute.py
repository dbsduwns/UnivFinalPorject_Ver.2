from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field


TransportType = Literal["bus", "shuttle", "subway", "walking", "mixed"]
DestinationType = Literal["building", "shuttle_stop", "campus_gate"]
CommuteStatus = Literal[
    "setup_required",
    "ready",
    "no_schedule",
    "no_route",
    "provider_error",
]
DisplayMode = Literal["departure_recommendation", "travel_time_only"]
CommuteCalculationMode = Literal["class_arrival", "depart_now"]
RouteCategory = Literal[
    "google_recommended",
    "fastest",
    "least_walking",
    "fewest_transfers",
]
RealtimeRouteStatus = Literal[
    "catchable",
    "next_bus",
    "late",
    "not_applicable",
    "no_realtime_data",
]


class CommuteProfileCreate(BaseModel):
    home_address: str = Field(min_length=1, max_length=255)
    home_road_address: str | None = Field(default=None, max_length=255)
    home_latitude: float | None = Field(default=None, ge=-90, le=90)
    home_longitude: float | None = Field(default=None, ge=-180, le=180)
    use_shuttle: bool = False
    departure_buffer_minutes: int = Field(default=10, ge=0, le=120)


class CommuteProfileUpdate(BaseModel):
    home_address: str | None = Field(default=None, min_length=1, max_length=255)
    home_road_address: str | None = Field(default=None, max_length=255)
    home_latitude: float | None = Field(default=None, ge=-90, le=90)
    home_longitude: float | None = Field(default=None, ge=-180, le=180)
    use_shuttle: bool | None = None
    shuttle_destination: str | None = Field(default=None, max_length=100)
    departure_buffer_minutes: int | None = Field(default=None, ge=0, le=120)


class CommuteSettingsUpdate(BaseModel):
    use_shuttle: bool | None = None
    departure_buffer_minutes: int | None = Field(default=None, ge=0, le=120)


class CommuteAddressSearchResult(BaseModel):
    address: str
    road_address: str | None = None
    building_name: str | None = None
    latitude: float
    longitude: float


class CommuteProfileResponse(BaseModel):
    id: int
    user_id: int
    home_address: str
    home_road_address: str | None = None
    home_latitude: float
    home_longitude: float
    use_shuttle: bool
    shuttle_destination: str | None = None
    departure_buffer_minutes: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class FirstClassResponse(BaseModel):
    course_id: int | None = None
    course_name: str
    start_time: time
    end_time: time | None = None
    building_name: str | None = None
    room_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class CommuteDestinationResponse(BaseModel):
    destination_type: DestinationType
    destination_name: str
    latitude: float
    longitude: float


class RouteCoordinateResponse(BaseModel):
    latitude: float
    longitude: float


class RouteStepResponse(BaseModel):
    travel_mode: str
    duration_minutes: int = Field(default=0, ge=0)
    distance_meters: int = Field(default=0, ge=0)
    instruction: str | None = None
    transit_line_name: str | None = None
    transit_line_color: str | None = None
    vehicle_type: str | None = None
    departure_stop_name: str | None = None
    arrival_stop_name: str | None = None
    departure_stop_location: RouteCoordinateResponse | None = None
    arrival_stop_location: RouteCoordinateResponse | None = None
    transit_agency_name: str | None = None
    transit_headsign: str | None = None
    scheduled_departure_time: datetime | None = None
    stop_count: int | None = Field(default=None, ge=0)
    tago_city_code: str | None = None
    tago_route_id: str | None = None
    tago_boarding_stop_id: str | None = None
    next_vehicle_arrival_minutes: int | None = Field(default=None, ge=0)
    route_path: list[RouteCoordinateResponse] = Field(default_factory=list)


class RouteStopResponse(BaseModel):
    stop_order: int = Field(ge=0)
    stop_id: str
    stop_name: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class LiveBusPositionResponse(BaseModel):
    vehicle_number: str
    route_name: str | None = None
    direction: str | None = None
    destination_name: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    position_source: Literal["gps", "map_matched", "stop"] = "stop"
    current_stop_order: int | None = Field(default=None, ge=0)
    current_stop_id: str | None = None
    current_stop_name: str | None = None


class TransitArrivalResponse(BaseModel):
    """탑승 정류장 기준의 다음 대중교통 도착 예정 정보."""

    vehicle_number: str
    arrival_minutes: int = Field(ge=0)
    direction: str | None = None
    destination_name: str | None = None
    arrival_message: str | None = None


class LiveBusPositionsResponse(BaseModel):
    city_code: str
    route_id: str
    cached_at: datetime
    cache_ttl_seconds: int = Field(default=15, ge=1)
    vehicles: list[LiveBusPositionResponse] = Field(default_factory=list)
    route_stops: list[RouteStopResponse] = Field(default_factory=list)


class TransitLiveRequest(BaseModel):
    """구간을 펼칠 때만 지연 조회하는 Google 정류장 설명 정보."""
    route_name: str = Field(min_length=1, max_length=120)
    vehicle_type: str = Field(min_length=1, max_length=40)
    departure_stop_name: str = Field(min_length=1, max_length=120)
    arrival_stop_name: str = Field(min_length=1, max_length=120)
    departure_stop_location: RouteCoordinateResponse | None = None
    arrival_stop_location: RouteCoordinateResponse | None = None
    agency_name: str = Field(default="", max_length=200)
    headsign: str = Field(default="", max_length=120)
    stop_count: int | None = Field(default=None, ge=0)
    # 화면에 그리는 Google 대중교통 구간을 방향 검증에도 재사용한다.
    # 지나치게 큰 요청을 막기 위해 프론트에서도 축약하고 서버에서도 상한을 둔다.
    route_path: list[RouteCoordinateResponse] = Field(default_factory=list, max_length=512)


class TransitLiveResponse(BaseModel):
    status: Literal["ok", "no_data", "unsupported", "unmatched", "not_configured", "provider_error"]
    provider: str | None = None
    message: str | None = None
    cached_at: datetime
    refresh_after_seconds: int = Field(default=30, ge=1)
    arrival_minutes: int | None = Field(default=None, ge=0)
    arrival_message: str | None = None
    vehicle_number: str | None = None
    vehicle_position_status: Literal["available", "fallback", "unavailable", "not_applicable"] = "unavailable"
    vehicle_position_reason: str | None = None
    vehicle_position_message: str | None = None
    boarding_stop_order: int | None = None
    alighting_stop_order: int | None = None
    route_stops: list[RouteStopResponse] = Field(default_factory=list)
    vehicles: list[LiveBusPositionResponse] = Field(default_factory=list)
    arrivals: list[TransitArrivalResponse] = Field(default_factory=list)


class RouteSummaryResponse(BaseModel):
    transport_type: TransportType
    route_category: RouteCategory | None = None
    route_name: str | None = None
    departure_time: time | None = None
    arrival_time: time | None = None
    duration_minutes: int = Field(ge=0)
    walking_minutes: int = Field(default=0, ge=0)
    transfer_count: int = Field(default=0, ge=0)
    buffer_minutes: int | None = Field(default=None, ge=0)
    boarding_stop_name: str | None = None
    bus_arrival_minutes: int | None = Field(default=None, ge=0)
    next_bus_arrival_minutes: int | None = Field(default=None, ge=0)
    selected_bus_arrival_minutes: int | None = Field(default=None, ge=0)
    bus_remaining_stops: int | None = Field(default=None, ge=0)
    realtime_status: RealtimeRouteStatus | None = None
    additional_wait_minutes: int = Field(default=0, ge=0)
    adjusted_arrival_time: time | None = None
    shuttle_departure_time: time | None = None
    shuttle_arrival_time: time | None = None
    is_recommended: bool = False
    recommendation_reason: str | None = None
    route_path: list[RouteCoordinateResponse] = Field(default_factory=list)
    route_steps: list[RouteStepResponse] = Field(default_factory=list)


class CommuteTodayResponse(BaseModel):
    status: CommuteStatus
    display_mode: DisplayMode | None = None
    message: str | None = None
    first_class: FirstClassResponse | None = None
    destination: CommuteDestinationResponse | None = None
    recommended_route: RouteSummaryResponse | None = None
    alternatives: list[RouteSummaryResponse] = Field(default_factory=list)
    calculated_at: datetime | None = None
    refresh_available_at: datetime | None = None
