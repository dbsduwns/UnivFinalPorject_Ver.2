import { apiClient } from "@/api/client";
import { ChatRoom, ChatMessage, ChatSendResponse } from "./types";

export const chatApi = {
    
    getRooms: () => apiClient.get<ChatRoom[]>("/api/chat/rooms"),
    
    createRoom: (title?: string) => apiClient.post<ChatRoom>("/api/chat/rooms", {title}),

    getMessages: (roomId: number) => apiClient.get<ChatMessage[]>(`/api/chat/rooms/${roomId}/messages`),

    sendMessage: (roomId: number, content: string) => apiClient.post<ChatSendResponse>(`/api/chat/rooms/${roomId}/messages`, {content}),

};