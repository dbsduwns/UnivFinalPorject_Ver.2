export interface ChatRoom {
    id: number;
    user_id: number;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ChatMessage {
    id: number;
    chat_room_id: number;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
    navigation_targets?: ChatNavigationTarget[];
}

export interface ChatNavigationTarget {
    type: 'notice' | 'meal' | 'shuttle';
    label: string;
    params: Record<string, string>;
}

export interface ChatSendResponse {
    room: ChatRoom;
    user_message: ChatMessage;
    assistant_message: ChatMessage;
}

export type ChatStreamStatus = 'searching' | 'generating';

export type ChatStreamEvent =
    | {
        type: 'start';
        room: ChatRoom;
        user_message: ChatMessage;
    }
    | {
        type: 'status';
        status: ChatStreamStatus;
    }
    | {
        type: 'delta';
        content: string;
    }
    | {
        type: 'navigation';
        targets: ChatNavigationTarget[];
    }
    | {
        type: 'done';
        room: ChatRoom;
        assistant_message: ChatMessage;
    }
    | {
        type: 'error';
        message: string;
    };
