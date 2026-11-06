export type NotificationData = Record<string, unknown>;

export type AppNotification = {
  id: number;
  notification_type: string;
  title: string;
  body: string;
  data: NotificationData;
  read_at: string | null;
  created_at: string;
};

export type NotificationCenterResponse = {
  items: AppNotification[];
  unread_count: number;
};
