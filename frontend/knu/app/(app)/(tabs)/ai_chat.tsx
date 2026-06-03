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
  Modal,
  Animated,
  Alert,
} from "react-native";
import { Send, Bot, User, Inbox, Plus, MessageSquare, X, Trash2, Edit3 } from "lucide-react-native";

import { AppScreenLayout } from "@/components/AppScreenLayout";
import { chatApi } from "@/features/chat/api/chat-api";
import { ChatMessage, ChatRoom } from "@/features/chat/types";

const DRAWER_WIDTH = 300;

export default function AIChatScreen() {
  const { q } = useLocalSearchParams<{ q?: string }>();
  const router = useRouter();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentRoom, setCurrentRoom] = useState<ChatRoom | null>(null);
  
  // Drawer 상태
  const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const slideAnim = useRef(new Animated.Value(-DRAWER_WIDTH)).current;

  const flatListRef = useRef<FlatList>(null);
  const hasProcessedQuery = useRef(false);
  const shouldScrollRef = useRef(false);

  // 채팅 삭제 & 이름 수정 모달 상태
  const [isSetModalOpen, setIsSetModalOpen] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState<ChatRoom | null>(null);
  const [editTitle, setEditTitle] = useState("");

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

    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      chat_room_id: targetRoom.id,
      role: "user",
      content: userContent,
      created_at: new Date().toISOString(),
    };

    shouldScrollRef.current = true;
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await chatApi.sendMessage(targetRoom.id, userContent);
      shouldScrollRef.current = true;
      setMessages((prev) => {
        const filtered = prev.filter(m => m.id !== tempUserMsg.id);
        return [...filtered, response.data.user_message, response.data.assistant_message];
      });
      
      // 채팅방 목록 최신화
      const roomsResponse = await chatApi.getRooms();
      setChatRooms(roomsResponse.data);
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
          "오늘 학식 메뉴 알려줘",
          "졸업 학점이 얼마나 남았지?",
          "내일 순환버스 시간표 보여줘"
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
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
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

          <FlatList
            ref={flatListRef}
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
          <View className="flex-1 justify-center items-center bg-black/50 px-6">
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
          </View>
        </Modal>
      </AppScreenLayout>
    </KeyboardAvoidingView>
  );
}
