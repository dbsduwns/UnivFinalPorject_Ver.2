import React, { useState, useEffect, useRef } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { Send, Bot, User } from "lucide-react-native";

import { AppScreenLayout } from "@/components/AppScreenLayout";
import { chatApi } from "@/features/chat/api/chat-api";
import { ChatMessage, ChatRoom } from "@/features/chat/types";

export default function AIChatScreen() {
  const { q } = useLocalSearchParams<{ q?: string }>();
  const router = useRouter();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentRoom, setCurrentRoom] = useState<ChatRoom | null>(null);
  
  const flatListRef = useRef<FlatList>(null);
  const hasProcessedQuery = useRef(false);

  const shouldScrollRef = useRef(false);

  const onSend = async (content: string) => {
    if (!content.trim() || !currentRoom || isLoading) return;

    const userContent = content.trim();
    setInputText("");
    setIsLoading(true);

    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      chat_room_id: currentRoom.id,
      role: "user",
      content: userContent,
      created_at: new Date().toISOString(),
    };

    shouldScrollRef.current = true;
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await chatApi.sendMessage(currentRoom.id, userContent);
      shouldScrollRef.current = true;
      setMessages((prev) => {
        const filtered = prev.filter(m => m.id !== tempUserMsg.id);
        return [...filtered, response.data.user_message, response.data.assistant_message];
      });
    } catch (error: any) {
      console.error("Failed to send message:", error);
      if (error.code === 'ECONNABORTED') {
        alert("요청 시간이 초과되었습니다. (서버 응답 지연)");
      } else if (error.message === 'Network Error') {
        alert("네트워크 연결이 원활하지 않습니다. Wi-Fi 상태를 확인해 주세요.");
      } else {
        alert("메시지 전송에 실패했습니다.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const initChat = async () => {
      try {
        const roomsResponse = await chatApi.getRooms();
        let room = roomsResponse.data[0];

        if (!room) {
          const createResponse = await chatApi.createRoom("New Chat");
          room = createResponse.data;
        }

        setCurrentRoom(room);
        const messagesResponse = await chatApi.getMessages(room.id);
        shouldScrollRef.current = true;
        setMessages(messagesResponse.data);
      } catch (error) {
        console.error("Failed to initialize chat:", error);
      }
    };

    initChat();
  }, []);

  useEffect(() => {
    if (messages.length > 0 && shouldScrollRef.current) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
        shouldScrollRef.current = false;
      }, 100);
    }
  }, [messages]);

  useEffect(() => {
    if (q && currentRoom && !hasProcessedQuery.current) {
      hasProcessedQuery.current = true;
      onSend(q);
      router.setParams({ q: "" });
    }
  }, [q, currentRoom]);

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isAssistant = item.role === "assistant";
    return (
      <View
        className={`flex-row my-2 px-4 ${
          isAssistant ? "justify-start" : "justify-end"
        }`}
      >
        {isAssistant && (
          <View className="w-8 h-8 rounded-full bg-blue-600 items-center justify-center mr-2">
            <Bot size={18} color="white" />
          </View>
        )}
        <View
          className={`max-w-[80%] p-3 rounded-2xl ${
            isAssistant
              ? "bg-gray-200 rounded-tl-none"
              : "bg-blue-500 rounded-tr-none"
          }`}
        >
          <Text className={isAssistant ? "text-gray-800" : "text-white"}>
            {item.content}
          </Text>
        </View>
        {!isAssistant && (
          <View className="w-8 h-8 rounded-full bg-gray-400 items-center justify-center ml-2">
            <User size={18} color="white" />
          </View>
        )}
      </View>
    );
  };

  return (
    
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={{ flex: 1 }}
      keyboardVerticalOffset={Platform.OS === "ios"? 90 : 0}
    >
      <AppScreenLayout>
        <View style={{ flex: 1, backgroundColor: 'white' }}>
          <View className="py-3 border-b border-gray-100 items-center bg-white">
            <Text className="font-bold text-base text-gray-800">AI 비서</Text>
          </View>

          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderMessage}
            contentContainerStyle={{ paddingVertical: 10, paddingBottom: 20 }}
          />

          <View className="p-4 bg-white border-t border-gray-100 flex-row items-center">
            <TextInput
              className="flex-1 bg-gray-50 text-gray-900 rounded-2xl px-4 py-3 mr-2 border border-gray-200"
              style={{ maxHeight: 100 }}
              placeholder="궁금한 것을 물어보세요..."
              placeholderTextColor="#9ca3af"
              value={inputText}
              onChangeText={setInputText}
              multiline
            />
            <TouchableOpacity
              onPress={() => onSend(inputText)}
              disabled={isLoading || !inputText.trim()}
              className="w-12 h-12 rounded-full items-center justify-center bg-blue-600 shadow-sm"
              style={{ opacity: (isLoading || !inputText.trim()) ? 0.5 : 1 }}
            >
              {isLoading ? (
                <ActivityIndicator size="small" color="white" />
              ) : (
                <Send size={20} color="white" />
              )}
            </TouchableOpacity>
          </View>
        </View>
      </AppScreenLayout>
    </KeyboardAvoidingView>
  );
}
