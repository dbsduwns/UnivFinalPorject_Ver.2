import { apiClient } from "@/api/client";
import type {
  FriendRequestsSummary,
  FriendSearchItem,
  FriendTimetableResponse,
  FriendUser,
} from "./types";
import type { Timetable } from "@/features/timetable/api/types";

export const searchFriends = async (query: string): Promise<FriendSearchItem[]> => {
  const { data } = await apiClient.get<FriendSearchItem[]>("/api/friends/search", {
    params: { query },
  });
  return data;
};

export const sendFriendRequest = async (body: {
  addressee_id?: number;
  student_id?: string;
}): Promise<{ message: string; request_id: number; status: string }> => {
  const { data } = await apiClient.post("/api/friends/requests", body);
  return data;
};

export const getFriendRequests = async (): Promise<FriendRequestsSummary> => {
  const { data } = await apiClient.get<FriendRequestsSummary>("/api/friends/requests");
  return data;
};

export const acceptFriendRequest = async (
  requestId: number
): Promise<{ message: string; request_id: number; status: string }> => {
  const { data } = await apiClient.post(`/api/friends/requests/${requestId}/accept`);
  return data;
};

export const rejectFriendRequest = async (
  requestId: number
): Promise<{ message: string }> => {
  const { data } = await apiClient.post(`/api/friends/requests/${requestId}/reject`);
  return data;
};

export const cancelFriendRequest = async (
  requestId: number
): Promise<{ message: string }> => {
  const { data } = await apiClient.delete(`/api/friends/requests/${requestId}`);
  return data;
};

export const getFriends = async (): Promise<FriendUser[]> => {
  const { data } = await apiClient.get<FriendUser[]>("/api/friends/");
  return data;
};

export const deleteFriend = async (friendId: number): Promise<{ message: string }> => {
  const { data } = await apiClient.delete(`/api/friends/${friendId}`);
  return data;
};

export const getFriendTimetables = async (friendId: number): Promise<Timetable[]> => {
  const { data } = await apiClient.get<Timetable[]>(`/api/friends/${friendId}/timetables`);
  return data;
};

export const getFriendTimetable = async (
  friendId: number,
  timetableId?: number
): Promise<FriendTimetableResponse> => {
  const { data } = await apiClient.get<FriendTimetableResponse>(
    `/api/friends/${friendId}/timetable`,
    {
      params: timetableId ? { timetable_id: timetableId } : undefined,
    }
  );
  return data;
};
