import type { Timetable, TimetableDetail } from "@/features/timetable/api/types";

export type FriendUser = {
  id: number;
  email: string;
  name: string;
  student_id: string | null;
  department: string | null;
  grade: number | null;
  avatar_url: string | null;
};

export type FriendRequestItem = {
  id: number;
  status: "PENDING" | "ACCEPTED" | "REJECTED";
  created_at: string | null;
  user: FriendUser;
};

export type FriendRequestsSummary = {
  received: FriendRequestItem[];
  sent: FriendRequestItem[];
};

export type FriendshipStatus = "NONE" | "PENDING_SENT" | "PENDING_RECEIVED" | "FRIEND";

export type FriendSearchItem = {
  user: FriendUser;
  friendship_status: FriendshipStatus;
  request_id?: number | null;
};

export type FriendTimetableResponse = {
  friend: FriendUser;
  timetable: TimetableDetail | null;
  available_timetables: Timetable[];
};
