export interface ChatUserSummary {
  id: number;
  name: string;
  avatar_url: string | null;
}

export interface ChatParticipant {
  id: number;
  user_id: number;
  last_read: string | null;
  user: ChatUserSummary | null;
}

export interface ChatRoom {
  id: number;
  is_group: boolean;
  name: string | null;
  created_at: string;
  updated_at: string;
  participants: ChatParticipant[];
}

export interface ChatRoomCreateRequest {
  friend_id?: number;
  participant_ids?: number[];
  name?: string;
}

export interface ChatMessage {
  id: number;
  room_messenger_id: number;
  sender_id: number;
  content: string;
  created_at: string;
}

export interface ChatSendResponse {
  message: ChatMessage;
}
