import { apiClient } from "@/api/client";
import { ChatRoom, ChatMessage, ChatSendResponse } from "./types";

export const chatApi = {
    
    getRooms: () => apiClient.get<ChatRoom[]>("/api/ai/chat/rooms"),
    
    createRoom: (title?: string) => apiClient.post<ChatRoom>("/api/ai/chat/rooms", {title}),

    getMessages: (roomId: number) => apiClient.get<ChatMessage[]>(`/api/ai/chat/rooms/${roomId}/messages`),

    sendMessage: (roomId: number, content: string) => apiClient.post<ChatSendResponse>(`/api/ai/chat/rooms/${roomId}/messages`, {content}),

    deleteRoom: (roomId: number) => apiClient.delete(`/api/ai/chat/rooms/${roomId}`),

    updateRoom: (roomId: number, title: string) =>
        apiClient.patch<ChatRoom>(`/api/ai/chat/rooms/${roomId}`, {title}),

};
