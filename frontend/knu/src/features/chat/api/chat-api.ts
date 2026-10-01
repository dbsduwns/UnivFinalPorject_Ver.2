import { apiClient } from "@/api/client";
import type { ChatRoom, ChatMessage, ChatRoomCreateRequest, ChatSendResponse } from "../types";

export const chatApi = {
  getRooms: () => apiClient.get<ChatRoom[]>("/api/chat/rooms"),

  // 1:1: { friend_id }, 단체방: { participant_ids, name }
  createRoom: (request: ChatRoomCreateRequest) =>
    apiClient.post<ChatRoom>("/api/chat/rooms", request),

  getMessages: (roomId: number) =>
    apiClient.get<ChatMessage[]>(`/api/chat/rooms/${roomId}/messages`),

  sendMessage: (roomId: number, content: string) =>
    apiClient.post<ChatSendResponse>(`/api/chat/rooms/${roomId}/messages`, { content }),

  // 현재 사용자만 대화방에서 나갑니다.
  deleteRoom: (roomId: number) =>
    apiClient.delete(`/api/chat/rooms/${roomId}`),
};
