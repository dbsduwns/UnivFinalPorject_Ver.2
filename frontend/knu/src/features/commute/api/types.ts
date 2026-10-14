export type TransportType = "bus" | "shuttle" | "subway" | "walking" | "mixed";
export type DestinationType = "building" | "shuttle_stop" | "campus_gate";
export type CommuteStatus =
  | "setup_required"
  | "ready"
  | "no_schedule"
  | "no_route"
  | "provider_error";
export type DisplayMode = "departure_recommendation" | "travel_time_only";

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
  route_name: string | null;
  departure_time: string | null;
  arrival_time: string | null;
  duration_minutes: number;
  walking_minutes: number;
  transfer_count: number;
  buffer_minutes: number | null;
  boarding_stop_name: string | null;
  bus_arrival_minutes: number | null;
  bus_remaining_stops: number | null;
  shuttle_departure_time: string | null;
  shuttle_arrival_time: string | null;
  is_recommended: boolean;
  recommendation_reason: string | null;
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
};
