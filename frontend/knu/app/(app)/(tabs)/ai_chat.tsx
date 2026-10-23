import React, { useState, useEffect, useRef } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Animated,
  Alert,
} from "react-native";
import { Send, Bot, User, Inbox, Plus, MessageSquare, X, Trash2, Edit3, Square } from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { chatApi } from "@/features/ai_chat/api/ai_chat";
import type { ChatMessage, ChatRoom, ChatStreamStatus } from "@/features/ai_chat/api/types";

const DRAWER_WIDTH = 300;

export default function AIChatScreen() {
  const { q } = useLocalSearchParams<{ q?: string }>();
  const router = useRouter();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(Keyboard.isVisible());
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<ChatStreamStatus | null>(null);
  const [currentRoom, setCurrentRoom] = useState<ChatRoom | null>(null);
  
  // Drawer 상태
  const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const slideAnim = useRef(new Animated.Value(-DRAWER_WIDTH)).current;

  const flatListRef = useRef<FlatList>(null);
  const hasProcessedQuery = useRef(false);
  const shouldScrollRef = useRef(false);
  const streamAbortControllerRef = useRef<AbortController | null>(null);

  // 채팅 삭제 & 이름 수정 모달 상태
  const [isSetModalOpen, setIsSetModalOpen] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState<ChatRoom | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const stopStreaming = () => {
    streamAbortControllerRef.current?.abort();
    streamAbortControllerRef.current = null;
    setStreamStatus(null);
    setIsStreaming(false);
  };

  const openDrawer = () => {
    setIsDrawerOpen(true);
    Animated.timing(slideAnim, {
      toValue: 0,
      duration: 250,
      useNativeDriver: true,
    }).start();
  };

  const closeDrawer = () => {
    Animated.timing(slideAnim, {
      toValue: -DRAWER_WIDTH,
      duration: 250,
      useNativeDriver: true,
    }).start(() => setIsDrawerOpen(false));
  };

  const loadRoom = async (room: ChatRoom) => {
    if (isStreaming) {
      Alert.alert("답변 작성 중", "현재 답변을 중단한 뒤 채팅방을 이동해 주세요.");
      return;
    }
    closeDrawer();
    if (currentRoom?.id === room.id) return;
    
    setCurrentRoom(room);
    setMessages([]);
    setIsLoading(true);
    try {
      const response = await chatApi.getMessages(room.id);
      shouldScrollRef.current = true;
      setMessages(response.data);
    } catch (error) {
      console.error("Failed to load messages", error);
      alert("메시지를 불러오는데 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const createNewRoom = async () => {
    if (isStreaming) {
      Alert.alert("답변 작성 중", "현재 답변을 중단한 뒤 새 채팅을 시작해 주세요.");
      return;
    }
    closeDrawer();
    setIsLoading(true);
    try {
      const response = await chatApi.createRoom("새로운 채팅");
      setChatRooms((prev) => [response.data, ...prev]);
      setCurrentRoom(response.data);
      setMessages([]);
    } catch (error) {
      console.error("Failed to create room", error);
      alert("채팅방 생성에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLongPress = (room: ChatRoom) => {
    setSelectedRoom(room);
    setEditTitle(room.title || "새로운 채팅");
    setIsSetModalOpen(true);
  };

  const handleDeleteRoom = async () => {
    if (!selectedRoom) return;

    Alert.alert(
      "채팅방 삭제",
      "이 채팅방의 모든 대화 내용이 삭제됩니다. 정말 삭제하시겠습니까?",
      [
        { text: "취소", style: "cancel" },
        {
          text: "삭제",
          style: "destructive",
          onPress: async () => {
            try {
              await chatApi.deleteRoom(selectedRoom.id);
              const updatedRooms = chatRooms.filter(r => r.id !== selectedRoom.id);
              setChatRooms(updatedRooms);
              
              if (currentRoom?.id === selectedRoom.id) {
                if (updatedRooms.length > 0) {
                  loadRoom(updatedRooms[0]);
                } else {
                  createNewRoom();
                }
              }
              setIsSetModalOpen(false);
            } catch (error) {
              console.error("Failed to delete room", error);
              alert("채팅방 삭제에 실패했습니다.");
            }
          }
        }
      ]
    );
  };

  const handleUpdateTitle = async () => {
    if (!selectedRoom || !editTitle.trim()) return;

    try {
      const response = await chatApi.updateRoom(selectedRoom.id, editTitle.trim());
      setChatRooms(prev => prev.map(r => r.id === selectedRoom.id ? response.data : r));
      if (currentRoom?.id === selectedRoom.id) {
        setCurrentRoom(response.data);
      }
      setIsSetModalOpen(false);
    } catch (error) {
      console.error("Failed to update title", error);
      alert("제목 수정에 실패했습니다.");
    }
  };

  const onSend = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userContent = content.trim();
    setInputText("");
    setIsLoading(true);

    let targetRoom = currentRoom;

    // 만약 현재 선택된 채팅방이 없다면 새 채팅방 생성
    if (!targetRoom) {
      try {
        const createResponse = await chatApi.createRoom("새로운 채팅");
        targetRoom = createResponse.data;
        setCurrentRoom(targetRoom);
        setChatRooms((prev) => [targetRoom!, ...prev]);
      } catch (error) {
        console.error("Failed to create room on demand", error);
        alert("채팅방 생성에 실패했습니다.");
        setIsLoading(false);
        return;
      }
    }

    const requestId = Date.now();
    const tempUserId = -requestId;
    const tempAssistantId = -(requestId + 1);
    const createdAt = new Date().toISOString();
    const tempUserMessage: ChatMessage = {
      id: tempUserId,
      chat_room_id: targetRoom.id,
      role: "user",
      content: userContent,
      created_at: createdAt,
    };
    const tempAssistantMessage: ChatMessage = {
      id: tempAssistantId,
      chat_room_id: targetRoom.id,
      role: "assistant",
      content: "",
      created_at: createdAt,
    };

    shouldScrollRef.current = true;
    setMessages((prev) => [...prev, tempUserMessage, tempAssistantMessage]);

    const controller = new AbortController();
    streamAbortControllerRef.current = controller;
    setIsStreaming(true);
    setStreamStatus("searching");

    try {
      await chatApi.streamMessage(
        targetRoom.id,
        userContent,
        (event) => {
          shouldScrollRef.current = true;

          if (event.type === "start") {
            setCurrentRoom(event.room);
            setChatRooms((previous) =>
              previous.map((room) =>
                room.id === event.room.id ? event.room : room,
              ),
            );
            setMessages((previous) =>
              previous.map((message) =>
                message.id === tempUserId ? event.user_message : message,
              ),
            );
            return;
          }

          if (event.type === "status") {
            setStreamStatus(event.status);
            return;
          }

          if (event.type === "delta") {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === tempAssistantId
                  ? { ...message, content: message.content + event.content }
                  : message,
              ),
            );
            return;
          }

          if (event.type === "done") {
            setCurrentRoom(event.room);
            setStreamStatus(null);
            setMessages((previous) =>
              previous.map((message) =>
                message.id === tempAssistantId
                  ? event.assistant_message
                  : message,
              ),
            );
          }
        },
        controller.signal,
      );

      const roomsResponse = await chatApi.getRooms();
      setChatRooms(roomsResponse.data);
    } catch (error: unknown) {
      if (!controller.signal.aborted) {
        console.error("Failed to stream message:", error);
        const message =
          error instanceof Error
            ? error.message
            : "메시지 전송에 실패했습니다.";
        Alert.alert("답변 생성 실패", message);
      }

      try {
        const messagesResponse = await chatApi.getMessages(targetRoom.id);
        setMessages(messagesResponse.data);
      } catch (refreshError) {
        console.error("Failed to refresh messages after stream error", refreshError);
      }
    } finally {
      if (streamAbortControllerRef.current === controller) {
        streamAbortControllerRef.current = null;
      }
      setStreamStatus(null);
      setIsStreaming(false);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const initChat = async () => {
      try {
        const roomsResponse = await chatApi.getRooms();
        setChatRooms(roomsResponse.data);
        
        let room = roomsResponse.data[0];

        if (room) {
          setCurrentRoom(room);
          const messagesResponse = await chatApi.getMessages(room.id);
          shouldScrollRef.current = true;
          setMessages(messagesResponse.data);
        } else {
          // 채팅방이 하나도 없는 경우 빈 상태 유지 (onSend에서 생성됨)
          setCurrentRoom(null);
          setMessages([]);
        }
      } catch (error) {
        console.error("Failed to initialize chat:", error);
      }
    };

    initChat();
  }, []);

  useEffect(() => {
    const showSubscription = Keyboard.addListener("keyboardDidShow", () => {
      setIsKeyboardVisible(true);
    });
    const hideSubscription = Keyboard.addListener("keyboardDidHide", () => {
      setIsKeyboardVisible(false);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  useEffect(() => {
    return () => {
      streamAbortControllerRef.current?.abort();
    };
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
    if (q && !hasProcessedQuery.current) {
      hasProcessedQuery.current = true;
      onSend(q);
      router.setParams({ q: "" });
    }
  }, [q, currentRoom]);

  const renderEmptyComponent = () => (
    <View className="flex-1 items-center justify-center pt-20 px-10">
      <View className="w-20 h-20 bg-blue-50 rounded-full items-center justify-center mb-6">
        <Bot size={40} color="#2563eb" />
      </View>
      <Text className="text-xl font-bold text-gray-900 mb-2 text-center">
        무엇을 도와드릴까요?
      </Text>
      <Text className="text-gray-500 text-center leading-6">
        캠퍼스 생활, 수강 신청, 학식 정보 등{"\n"}
        궁금한 것을 물어보세요!
      </Text>
      
      <View className="mt-10 w-full">
        <Text className="text-xs font-bold text-gray-400 mb-3 ml-1 uppercase tracking-widest">추천 질문</Text>
        {[
          "이번달 학사일정 알려줘",
          "최근 취업 관련 공지사항 보내줘",
          "오늘 수업 일정이 어떻게 되지?"
        ].map((item, index) => (
          <TouchableOpacity 
            key={index}
            className="bg-gray-50 border border-gray-100 p-4 rounded-2xl mb-2"
            onPress={() => onSend(item)}
          >
            <Text className="text-gray-700">{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isAssistant = item.role === "assistant";
    const displayedContent =
      isAssistant && !item.content
        ? streamStatus === "searching"
          ? "관련 정보를 찾고 있어요..."
          : "답변을 작성하고 있어요..."
        : item.content;
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
          <Text
            className={isAssistant ? "text-gray-800" : "text-white"}
            style={{ lineHeight: 22 }}
            selectable={isAssistant}
          >
            {displayedContent}
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
    <AppScreenLayout>
      <View style={{ flex: 1, backgroundColor: 'white' }}>
        <View className="py-3 border-b border-gray-100 flex-row items-center justify-center bg-white px-4 relative">
          <TouchableOpacity
            className="absolute left-4"
            onPress={openDrawer}
          >
            <Inbox size={24} color="#374151" />
          </TouchableOpacity>
          <Text className="font-bold text-base text-gray-800">AI 비서</Text>
        </View>
        {/* 채팅  */}
        <FlatList
          ref={flatListRef}
          style={{ flex: 1 }}
          data={messages}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderMessage}
          ListEmptyComponent={renderEmptyComponent}
          contentContainerStyle={{
            paddingVertical: 10,
            paddingBottom: 20,
            flexGrow: 1
          }}
        />
        {/* 채팅 입력창 */}
        <KeyboardAvoidingView
          behavior="padding"
          enabled={isKeyboardVisible}
          keyboardVerticalOffset={90}
        >
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
              onPress={isStreaming ? stopStreaming : () => onSend(inputText)}
              disabled={!isStreaming && (isLoading || !inputText.trim())}
              className={`w-12 h-12 rounded-full items-center justify-center shadow-sm ${
                isStreaming ? "bg-red-500" : "bg-blue-600"
              }`}
              style={{
                opacity: !isStreaming && (isLoading || !inputText.trim()) ? 0.5 : 1,
              }}
            >
              {isStreaming ? (
                <Square size={18} color="white" fill="white" />
              ) : isLoading ? (
                <ActivityIndicator size="small" color="white" />
              ) : (
                <Send size={20} color="white" />
              )}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </View>

        {/* Custom Drawer */}
        <Modal
          visible={isDrawerOpen}
          transparent={true}
          animationType="none"
          onRequestClose={closeDrawer}
        >
          <View style={{ flex: 1, flexDirection: 'row' }}>
            <TouchableOpacity
              style={{
                position: 'absolute',
                top: 0, bottom: 0, left: 0, right: 0,
                backgroundColor: 'rgba(0,0,0,0.5)',
              }}
              activeOpacity={1}
              onPress={closeDrawer}
            />
            
            <Animated.View
              style={{
                width: DRAWER_WIDTH,
                height: '100%',
                backgroundColor: 'white',
                transform: [{ translateX: slideAnim }],
                paddingTop: Platform.OS === 'ios' ? 50 : 20,
                shadowColor: '#000',
                shadowOffset: { width: 2, height: 0 },
                shadowOpacity: 0.25,
                shadowRadius: 5,
                elevation: 5,
              }}
            >
              <View className="px-4 pb-4 border-b border-gray-100 flex-row justify-between items-center">
                <Text className="font-bold text-lg text-gray-800">채팅 목록</Text>
                <TouchableOpacity onPress={closeDrawer}>
                  <X size={24} color="#374151" />
                </TouchableOpacity>
              </View>
              
              <TouchableOpacity 
                className="m-4 bg-blue-50 flex-row items-center justify-center py-3 rounded-xl border border-blue-100"
                onPress={createNewRoom}
              >
                <Plus size={20} color="#2563eb" />
                <Text className="text-blue-600 font-bold ml-2">새로운 채팅 시작</Text>
              </TouchableOpacity>

              <FlatList
                data={chatRooms}
                keyExtractor={item => item.id.toString()}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    className={`px-4 py-4 border-b border-gray-50 flex-row items-center ${
                      currentRoom?.id === item.id ? 'bg-blue-50' : ''
                    }`}
                    onPress={() => loadRoom(item)}
                    onLongPress={() => handleLongPress(item)}
                  >
                    <MessageSquare size={20} color={currentRoom?.id === item.id ? '#2563eb' : '#6b7280'} className="mr-3" />
                    <View className="flex-1">
                      <Text className={`font-medium ${currentRoom?.id === item.id ? 'text-blue-700' : 'text-gray-800'}`} numberOfLines={1}>
                        {item.title || "새로운 채팅"}
                      </Text>
                      <Text className="text-xs text-gray-500 mt-1">
                        {new Date(item.created_at).toLocaleDateString()}
                      </Text>
                    </View>
                  </TouchableOpacity>
                )}
              />
            </Animated.View>
          </View>
        </Modal>

        {/* 채팅방 설정 모달 (삭제/수정) */}
        <Modal
          visible={isSetModalOpen}
          transparent={true}
          animationType="fade"
          onRequestClose={() => setIsSetModalOpen(false)}
        >
          <KeyboardAvoidingView
            className="flex-1 justify-center items-center bg-black/50 px-6"
            behavior={Platform.OS === "ios" ? "padding" : "height"}
          >
            <View className="bg-white w-full rounded-3xl p-6 shadow-xl">
              <View className="flex-row justify-between items-center mb-6">
                <Text className="text-xl font-bold text-gray-900">채팅방 설정</Text>
                <TouchableOpacity onPress={() => setIsSetModalOpen(false)}>
                  <X size={24} color="#9ca3af" />
                </TouchableOpacity>
              </View>

              <View className="mb-6">
                <Text className="text-sm font-medium text-gray-500 mb-2 ml-1">채팅방 이름 수정</Text>
                <View className="flex-row items-center bg-gray-50 border border-gray-200 rounded-xl px-3">
                  <Edit3 size={18} color="#9ca3af" className="mr-2" />
                  <TextInput
                    className="flex-1 py-3 text-gray-900"
                    value={editTitle}
                    onChangeText={setEditTitle}
                    placeholder="채팅방 이름을 입력하세요"
                  />
                </View>
              </View>

              <View className="flex-row gap-3">
                <TouchableOpacity
                  className="flex-1 bg-red-50 border border-red-100 py-4 rounded-2xl flex-row items-center justify-center"
                  onPress={handleDeleteRoom}
                >
                  <Trash2 size={20} color="#ef4444" className="mr-2" />
                  <Text className="text-red-600 font-bold">삭제</Text>
                </TouchableOpacity>
                
                <TouchableOpacity
                  className="flex-2 bg-blue-600 py-4 rounded-2xl items-center justify-center"
                  onPress={handleUpdateTitle}
                  style={{ flex: 2 }}
                >
                  <Text className="text-white font-bold text-base">저장하기</Text>
                </TouchableOpacity>
              </View>
            </View>
          </KeyboardAvoidingView>
        </Modal>
    </AppScreenLayout>
  );
}
