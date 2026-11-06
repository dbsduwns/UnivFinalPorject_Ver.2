import { apiClient } from "@/api/client";
import type { AppUpdateCheckResponse } from "@/features/app-update/types";


export async function checkAndroidAppUpdate(currentVersionCode: number) {
  const { data } = await apiClient.get<AppUpdateCheckResponse>("/api/app-updates/android", {
    params: { current_version_code: currentVersionCode },
  });
  return data;
}
