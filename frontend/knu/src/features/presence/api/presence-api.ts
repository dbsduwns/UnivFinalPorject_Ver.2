import { apiClient } from "@/api/client";

import type { UserPresence, UserPresenceUpdateRequest } from "../types";

export const presenceApi = {
  updateMyPresence: (request: UserPresenceUpdateRequest) =>
    apiClient.put<UserPresence>("/api/presence", request),
};
