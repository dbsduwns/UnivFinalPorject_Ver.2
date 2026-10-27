export type UserPresence = {
  id: number;
  user_id: number;
  active_room_id: number | null;
  is_app_foreground: boolean;
  last_seen_at: string;
};

export type UserPresenceUpdateRequest = {
  active_room_id?: number | null;
  is_app_foreground: boolean;
};
