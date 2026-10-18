import { apiClient } from "@/api/client";
import { isAxiosError } from "axios";

import type {
  CommuteProfile,
  CommuteAddressSearchResult,
  CommuteProfileCreate,
  CommuteProfileUpdate,
  CommuteSettingsUpdate,
  CommuteToday,
  LiveBusPositions,
} from "./types";


export async function getTodayCommute(): Promise<CommuteToday> {
  const { data } = await apiClient.get<CommuteToday>("/api/commute/today");
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
