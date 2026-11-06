import { apiClient } from "@/api/client";
import type { AppNotification, NotificationCenterResponse } from "@/features/notifications/types";


export const notificationApi = {
  getNotifications: async () =>
    (await apiClient.get<NotificationCenterResponse>("/api/notifications", {
      params: { limit: 100 },
    })).data,

  markRead: async (notificationId: number) =>
    (await apiClient.patch<AppNotification>(`/api/notifications/${notificationId}/read`)).data,

  markAllRead: async () =>
    (await apiClient.post<{ updated_count: number }>("/api/notifications/read-all")).data,
};
