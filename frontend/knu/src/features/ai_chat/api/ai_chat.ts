import { fetch as expoFetch } from "expo/fetch";

import { apiClient } from "@/api/client";
import { API_BASE_URL } from "@/constants/config";
import { hrefLogin } from "@/constants/routes";
import * as tokenStorage from "@/features/auth/services/token-storage";

import type {
  ChatMessage,
  ChatRoom,
  ChatSendResponse,
  ChatStreamEvent,
} from "./types";

const decodeAscii = (value: Uint8Array): string => {
  let result = "";
  for (const byte of value) {
    result += String.fromCharCode(byte);
  }
  return result;
};

const readErrorMessage = async (response: Response): Promise<string> => {
  const fallback = `메시지 전송에 실패했습니다. (${response.status})`;
  try {
    const body: unknown = await response.json();
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string"
    ) {
      return body.detail;
    }
  } catch {
    // JSON 오류 본문이 아니면 상태 코드를 포함한 기본 메시지를 사용합니다.
  }
  return fallback;
};

export async function streamChatMessage(
  roomId: number,
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = await tokenStorage.getAccessToken();
  const response = await expoFetch(
    `${API_BASE_URL}/api/ai/chat/rooms/${roomId}/messages/stream`,
    {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/x-ndjson",
        "ngrok-skip-browser-warning": "true",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    },
  );

  if (!response.ok) {
    if (response.status === 401 && token) {
      await tokenStorage.clearTokens();
      const { useAuthStore } = await import("@/features/auth/store/auth-store");
      useAuthStore.getState().clearSession();
      const { router } = await import("expo-router");
      router.replace(hrefLogin);
    }
    throw new Error(await readErrorMessage(response));
  }

  if (!response.body) {
    throw new Error("스트림 응답을 읽을 수 없습니다.");
  }

  const reader = response.body.getReader();
  let buffer = "";
  let completed = false;

  const processLine = (line: string) => {
    if (!line.trim()) {
      return;
    }
    const event = JSON.parse(line) as ChatStreamEvent;
    onEvent(event);
    if (event.type === "done" || event.type === "fallback") {
      completed = true;
    } else if (event.type === "error") {
      throw new Error(event.message);
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decodeAscii(value);
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      lines.forEach(processLine);
    }

    processLine(buffer);
    if (!completed) {
      throw new Error("답변 스트림이 완료되기 전에 종료됐습니다.");
    }
  } finally {
    reader.releaseLock();
  }
}

export const chatApi = {
  getRooms: () => apiClient.get<ChatRoom[]>("/api/ai/chat/rooms"),

  createRoom: (title?: string) =>
    apiClient.post<ChatRoom>("/api/ai/chat/rooms", { title }),

  getMessages: (roomId: number) =>
    apiClient.get<ChatMessage[]>(`/api/ai/chat/rooms/${roomId}/messages`),

  sendMessage: (roomId: number, content: string) =>
    apiClient.post<ChatSendResponse>(`/api/ai/chat/rooms/${roomId}/messages`, {
      content,
    }),

  streamMessage: streamChatMessage,

  deleteRoom: (roomId: number) =>
    apiClient.delete(`/api/ai/chat/rooms/${roomId}`),

  updateRoom: (roomId: number, title: string) =>
    apiClient.patch<ChatRoom>(`/api/ai/chat/rooms/${roomId}`, { title }),
};
