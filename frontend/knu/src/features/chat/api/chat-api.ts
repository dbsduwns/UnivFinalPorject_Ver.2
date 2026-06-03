import { apiClient } from "@/api/client";
import { ChatRoom, ChatMessage, ChatSendResponse } from "../types";

export const chatApi = {
  // 채팅방 목록 가져오기
  getRooms: () => 
    apiClient.get<ChatRoom[]>("/api/chat/rooms"),

  // 새 채팅방 생성
  createRoom: (title?: string) => 
    apiClient.post<ChatRoom>("/api/chat/rooms", { title }),

  // 특정 채팅방의 메시지 내역 조회
  getMessages: (roomId: number) => 
    apiClient.get<ChatMessage[]>(`/api/chat/rooms/${roomId}/messages`),

  // 메시지 전송 및 AI 응답 받기
  sendMessage: (roomId: number, content: string) => 
    apiClient.post<ChatSendResponse>(`/api/chat/rooms/${roomId}/messages`, { content }),

  // 채팅방 삭제
  deleteRoom: (roomId: number) =>
    apiClient.delete(`/api/chat/rooms/${roomId}`),

  // 채팅방 제목 수정
  updateRoom: (roomId: number, title: string) =>
    apiClient.patch<ChatRoom>(`/api/chat/rooms/${roomId}`, { title }),
};
