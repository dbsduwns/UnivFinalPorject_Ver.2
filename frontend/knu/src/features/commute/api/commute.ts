import { apiClient } from "@/api/client";

import type {
  CommuteProfile,
  CommuteProfileCreate,
  CommuteProfileUpdate,
  CommuteSettingsUpdate,
  CommuteToday,
} from "./types";


export async function getTodayCommute(): Promise<CommuteToday> {
  const { data } = await apiClient.get<CommuteToday>("/api/commute/today");
  return data;
}

export async function getCommuteProfile(): Promise<CommuteProfile> {
  const { data } = await apiClient.get<CommuteProfile>("/api/commute/profile");
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
