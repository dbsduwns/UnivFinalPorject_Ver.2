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
    departure_stop_name: str | None = None
    arrival_stop_name: str | None = None
    route_path: list[RouteCoordinateResponse] = Field(default_factory=list)


class RouteSummaryResponse(BaseModel):
    transport_type: TransportType
    route_name: str | None = None
    departure_time: time | None = None
    arrival_time: time | None = None
    duration_minutes: int = Field(ge=0)
    walking_minutes: int = Field(default=0, ge=0)
    transfer_count: int = Field(default=0, ge=0)
    buffer_minutes: int | None = Field(default=None, ge=0)
    boarding_stop_name: str | None = None
    bus_arrival_minutes: int | None = Field(default=None, ge=0)
    bus_remaining_stops: int | None = Field(default=None, ge=0)
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
