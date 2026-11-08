export type TransportType = "bus" | "shuttle" | "subway" | "walking" | "mixed";
export type DestinationType = "building" | "shuttle_stop" | "campus_gate";
export type CommuteStatus =
  | "setup_required"
  | "ready"
  | "no_schedule"
  | "no_route"
  | "provider_error";
export type DisplayMode = "departure_recommendation" | "travel_time_only";
export type RouteCategory =
  | "google_recommended"
  | "fastest"
  | "least_walking"
  | "fewest_transfers";
export type RealtimeRouteStatus =
  | "catchable"
  | "next_bus"
  | "late"
  | "not_applicable"
  | "no_realtime_data";

export type CommuteProfile = {
  id: number;
  user_id: number;
  home_address: string;
  home_road_address: string | null;
  home_latitude: number;
  home_longitude: number;
  use_shuttle: boolean;
  shuttle_destination: string | null;
  departure_buffer_minutes: number;
  created_at: string | null;
  updated_at: string | null;
};

export type CommuteProfileCreate = {
  home_address: string;
  home_road_address?: string | null;
  home_latitude?: number;
  home_longitude?: number;
  use_shuttle?: boolean;
  departure_buffer_minutes?: number;
};

export type CommuteProfileUpdate = Partial<
  Pick<
    CommuteProfile,
    | "home_address"
    | "home_road_address"
    | "home_latitude"
    | "home_longitude"
    | "use_shuttle"
    | "shuttle_destination"
    | "departure_buffer_minutes"
  >
>;

export type CommuteSettingsUpdate = Partial<
  Pick<CommuteProfile, "use_shuttle" | "departure_buffer_minutes">
>;

export type CommuteAddressSearchResult = {
  address: string;
  road_address: string | null;
  building_name: string | null;
  latitude: number;
  longitude: number;
};

export type FirstClass = {
  course_id: number | null;
  course_name: string;
  start_time: string;
  end_time: string | null;
  building_name: string | null;
  room_name: string | null;
  latitude: number | null;
  longitude: number | null;
};

export type CommuteDestination = {
  destination_type: DestinationType;
  destination_name: string;
  latitude: number;
  longitude: number;
};

export type RouteSummary = {
  transport_type: TransportType;
  route_category: RouteCategory | null;
  route_name: string | null;
  departure_time: string | null;
  arrival_time: string | null;
  duration_minutes: number;
  walking_minutes: number;
  transfer_count: number;
  buffer_minutes: number | null;
  boarding_stop_name: string | null;
  bus_arrival_minutes: number | null;
  next_bus_arrival_minutes: number | null;
  selected_bus_arrival_minutes: number | null;
  bus_remaining_stops: number | null;
  realtime_status: RealtimeRouteStatus | null;
  additional_wait_minutes: number;
  adjusted_arrival_time: string | null;
  shuttle_departure_time: string | null;
  shuttle_arrival_time: string | null;
  is_recommended: boolean;
  recommendation_reason: string | null;
  route_path: RouteCoordinate[];
  route_steps: RouteStep[];
};

export type CommuteToday = {
  status: CommuteStatus;
  display_mode: DisplayMode | null;
  message: string | null;
  first_class: FirstClass | null;
  destination: CommuteDestination | null;
  recommended_route: RouteSummary | null;
  alternatives: RouteSummary[];
  calculated_at: string | null;
  refresh_available_at: string | null;
};

export type RouteCoordinate = {
  latitude: number;
  longitude: number;
};

export type RouteStep = {
  travel_mode: string;
  duration_minutes: number;
  distance_meters: number;
  instruction: string | null;
  transit_line_name: string | null;
  transit_line_color: string | null;
  vehicle_type: string | null;
  departure_stop_name: string | null;
  arrival_stop_name: string | null;
  departure_stop_location?: RouteCoordinate | null;
  arrival_stop_location?: RouteCoordinate | null;
  transit_agency_name?: string | null;
  transit_headsign?: string | null;
  scheduled_departure_time?: string | null;
  stop_count?: number | null;
  tago_city_code: string | null;
  tago_route_id: string | null;
  tago_boarding_stop_id: string | null;
  next_vehicle_arrival_minutes: number | null;
  route_path: RouteCoordinate[];
};

export type RouteStop = {
  stop_order: number;
  stop_id: string;
  stop_name: string;
  latitude: number | null;
  longitude: number | null;
};

export type LiveBusPosition = {
  vehicle_number: string;
  route_name: string | null;
  direction: string | null;
  destination_name: string | null;
  latitude: number | null;
  longitude: number | null;
  position_source: "gps" | "map_matched" | "stop";
  current_stop_order: number | null;
  current_stop_id: string | null;
  current_stop_name: string | null;
};

export type TransitArrival = {
  vehicle_number: string;
  arrival_seconds?: number | null;
  arrival_minutes: number;
  direction: string | null;
  destination_name: string | null;
  arrival_message: string | null;
};

export type TransitStopArrival = {
  stop_order: number;
  stop_id: string;
  stop_name: string;
  arrivals: TransitArrival[];
};

export type TransitAlternativeArrival = {
  route_id: string;
  route_name: string;
  arrival_seconds: number | null;
  arrival_minutes: number | null;
  boarding_stop_name: string;
  alighting_stop_name: string;
  is_recommended: boolean;
};

export type LiveBusPositions = {
  city_code: string;
  route_id: string;
  cached_at: string;
  cache_ttl_seconds: number;
  vehicles: LiveBusPosition[];
  route_stops: RouteStop[];
};

export type TransitLive = {
  status: "ok" | "no_data" | "unsupported" | "unmatched" | "not_configured" | "provider_error";
  provider: string | null;
  message: string | null;
  cached_at: string;
  refresh_after_seconds: number;
  arrival_minutes: number | null;
  arrival_message: string | null;
  vehicle_number: string | null;
  vehicle_position_status: "available" | "fallback" | "unavailable" | "not_applicable";
  vehicle_position_reason: string | null;
  vehicle_position_message: string | null;
  boarding_stop_order: number | null;
  alighting_stop_order: number | null;
  route_stops: RouteStop[];
  stop_arrivals: TransitStopArrival[];
  alternative_arrivals: TransitAlternativeArrival[];
  vehicles: LiveBusPosition[];
  arrivals: TransitArrival[];
};
