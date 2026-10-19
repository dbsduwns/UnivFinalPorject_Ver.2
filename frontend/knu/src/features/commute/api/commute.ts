import { apiClient } from "@/api/client";
import { isAxiosError } from "axios";
import { queryOptions } from "@tanstack/react-query";

import type {
  CommuteProfile,
  CommuteAddressSearchResult,
  CommuteProfileCreate,
  CommuteProfileUpdate,
  CommuteSettingsUpdate,
  CommuteToday,
  LiveBusPositions,
  TransitLive,
  RouteStep,
} from "./types";


export type CommuteCalculationMode = "class_arrival" | "depart_now";

export async function getTodayCommute(
  calculationMode: CommuteCalculationMode,
  signal?: AbortSignal,
): Promise<CommuteToday> {
  const { data } = await apiClient.get<CommuteToday>("/api/commute/today", {
    params: { calculation_mode: calculationMode },
    signal,
  });
  return data;
}

// 수업 기준 홈 예측과 현재 출발 지도 경로는 별도 캐시로 관리한다.
export const commuteTodayOptions = (
  userId: number | undefined,
  calculationMode: CommuteCalculationMode = "class_arrival",
) => queryOptions({
  queryKey: ["commute", "today", userId, calculationMode],
  queryFn: ({ signal }) => getTodayCommute(calculationMode, signal),
  staleTime: 60_000,
  gcTime: 5 * 60_000,
  retry: false,
  refetchOnReconnect: false,
  refetchOnWindowFocus: false,
});

export function transitLiveRequest(step: RouteStep) {
  return {
    route_name: step.transit_line_name ?? "",
    vehicle_type: step.vehicle_type ?? "",
    departure_stop_name: step.departure_stop_name ?? "",
    arrival_stop_name: step.arrival_stop_name ?? "",
    departure_stop_location: step.departure_stop_location ?? null,
    arrival_stop_location: step.arrival_stop_location ?? null,
    agency_name: step.transit_agency_name ?? "",
    headsign: step.transit_headsign ?? "",
  };
}

export async function getTransitLive(
  request: ReturnType<typeof transitLiveRequest>,
  signal?: AbortSignal,
): Promise<TransitLive> {
  const { data } = await apiClient.post<TransitLive>("/api/commute/transit-live", request, { signal });
  return data;
}

export async function getLiveBusPositions(
  cityCode: string,
  routeId: string,
): Promise<LiveBusPositions> {
  const { data } = await apiClient.get<LiveBusPositions>(
    "/api/commute/live-buses",
    { params: { city_code: cityCode, route_id: routeId } },
  );
  return data;
}

export async function getCommuteProfile(): Promise<CommuteProfile> {
  const { data } = await apiClient.get<CommuteProfile>("/api/commute/profile");
  return data;
}

export async function getCommuteProfileOrNull(): Promise<CommuteProfile | null> {
  try {
    return await getCommuteProfile();
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
}

export async function searchCommuteAddresses(
  query: string,
): Promise<CommuteAddressSearchResult[]> {
  const { data } = await apiClient.get<CommuteAddressSearchResult[]>(
    "/api/commute/addresses",
    { params: { q: query } },
  );
  return data;
}

export async function createCommuteProfile(
  body: CommuteProfileCreate,
): Promise<CommuteProfile> {
  const { data } = await apiClient.post<CommuteProfile>("/api/commute/profile", body);
  return data;
}

export async function updateCommuteProfile(
  body: CommuteProfileUpdate,
): Promise<CommuteProfile> {
  const { data } = await apiClient.patch<CommuteProfile>("/api/commute/profile", body);
  return data;
}

export async function updateCommuteSettings(
  body: CommuteSettingsUpdate,
): Promise<CommuteProfile> {
  const { data } = await apiClient.patch<CommuteProfile>("/api/commute/settings", body);
  return data;
}

export async function deleteCommuteProfile(): Promise<void> {
  await apiClient.delete("/api/commute/profile");
}
