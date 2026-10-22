import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { ArrowLeft, MessageCircle, Send, Users } from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { getAxiosErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { chatApi } from "@/features/chat/api/chat-api";
import type { ChatRoom } from "@/features/chat/types";

const BRAND = "#13708D";

const formatTime = (value: string) =>
  new Date(value).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });

export const ChatRoomsScreen = () => {
  const { friendId } = useLocalSearchParams<{ friendId?: string }>();
  const requestedFriendId = Number(friendId);
  const userId = useAuthStore((state) => state.user?.id);
  const client = useQueryClient();
  const { width } = useWindowDimensions();
  const isWide = width >= 760;
  const [selectedRoom, setSelectedRoom] = useState<ChatRoom | null>(null);
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const roomsQuery = useQuery({
    queryKey: ["chatRooms"],
    queryFn: async () => (await chatApi.getRooms()).data,
    refetchInterval: 10_000,
  });

  const createDirectRoom = useMutation({
    mutationFn: async (targetUserId: number) => (await chatApi.createRoom({ friend_id: targetUserId })).data,
    onSuccess: (room) => {
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
      setSelectedRoom(room);
    },
  });

  useEffect(() => {
    if (!Number.isInteger(requestedFriendId) || requestedFriendId <= 0 || createDirectRoom.isPending) return;
    createDirectRoom.mutate(requestedFriendId);
  }, [requestedFriendId]);

  const messagesQuery = useQuery({
    queryKey: ["chatMessages", selectedRoom?.id],
    queryFn: async () => (await chatApi.getMessages(selectedRoom!.id)).data,
    enabled: !!selectedRoom,
    refetchInterval: 5_000,
  });

  const sendMutation = useMutation({
    mutationFn: async (content: string) => (await chatApi.sendMessage(selectedRoom!.id, content)).data,
    onSuccess: () => {
      setDraft("");
      setSendError(null);
      void client.invalidateQueries({ queryKey: ["chatMessages", selectedRoom?.id] });
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
    },
    onError: (error) => setSendError(getAxiosErrorMessage(error, "메시지를 보내지 못했습니다.")),
  });

  const rooms = roomsQuery.data ?? [];
  const selectedRoomName = useMemo(() => getRoomName(selectedRoom, userId), [selectedRoom, userId]);
  const showConversation = isWide || !!selectedRoom;

  const send = () => {
    const content = draft.trim();
    if (!content || sendMutation.isPending || !selectedRoom) return;
    sendMutation.mutate(content);
  };

  return (
    <AppScreenLayout>
      <KeyboardAvoidingView className="flex-1 bg-[#F4F7F8]" behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View className="flex-1 p-3" style={{ gap: 12, flexDirection: isWide ? "row" : "column" }}>
          {(!showConversation || isWide) && (
            <View className="bg-white rounded-[28px] border border-gray-200 overflow-hidden" style={{ width: isWide ? "38%" : "100%" }}>
              <View className="px-5 pt-6 pb-4 border-b border-gray-100">
                <Text className="text-2xl font-extrabold text-gray-900">채팅</Text>
                <Text className="text-sm text-gray-400 mt-1">대화 중인 채팅방을 확인하세요.</Text>
              </View>
              {roomsQuery.isLoading ? (
                <View className="flex-1 items-center justify-center"><ActivityIndicator color={BRAND} /></View>
              ) : roomsQuery.isError ? (
                <View className="flex-1 items-center justify-center px-6">
                  <Text className="text-sm text-gray-500 text-center">채팅방을 불러오지 못했습니다.</Text>
                  <Pressable onPress={() => roomsQuery.refetch()} className="mt-4 px-4 py-2 rounded-xl bg-cyan-50"><Text className="font-bold" style={{ color: BRAND }}>다시 시도</Text></Pressable>
                </View>
              ) : rooms.length === 0 ? (
                <View className="flex-1 items-center justify-center px-8">
                  <View className="w-16 h-16 rounded-full bg-cyan-50 items-center justify-center"><MessageCircle size={30} color={BRAND} /></View>
                  <Text className="text-base font-extrabold text-gray-800 mt-4">아직 대화가 없습니다.</Text>
                  <Text className="text-xs text-gray-400 text-center mt-2">친구 화면에서 친구를 선택해 대화를 시작하세요.</Text>
                </View>
              ) : (
                <ScrollView contentContainerStyle={{ padding: 10 }} showsVerticalScrollIndicator={false}>
                  {rooms.map((room) => {
                    const active = selectedRoom?.id === room.id;
                    const name = getRoomName(room, userId);
                    return <Pressable key={room.id} onPress={() => setSelectedRoom(room)} className={`p-4 rounded-2xl mb-1 flex-row items-center ${active ? "bg-cyan-50" : "active:bg-gray-50"}`}>
                      <View className="w-11 h-11 rounded-full bg-cyan-100 items-center justify-center"><Text className="font-extrabold" style={{ color: BRAND }}>{name.slice(0, 1)}</Text></View>
                      <View className="flex-1 ml-3"><Text className="text-[15px] font-extrabold text-gray-900" numberOfLines={1}>{name}</Text><Text className="text-xs text-gray-400 mt-1">{room.is_group ? "그룹 채팅" : "개인 채팅"}</Text></View>
                    </Pressable>;
                  })}
                </ScrollView>
              )}
            </View>
          )}

          {showConversation && (
            <View className="flex-1 bg-white rounded-[28px] border border-gray-200 overflow-hidden">
              {selectedRoom ? <>
                <View className="h-[72px] px-4 border-b border-gray-100 flex-row items-center">
                  {!isWide && <Pressable onPress={() => setSelectedRoom(null)} className="w-10 h-10 rounded-full items-center justify-center mr-1"><ArrowLeft size={22} color="#334155" /></Pressable>}
                  <View className="w-10 h-10 rounded-full bg-cyan-100 items-center justify-center"><Text className="font-extrabold" style={{ color: BRAND }}>{selectedRoomName.slice(0, 1)}</Text></View>
                  <View className="flex-1 ml-3"><Text className="text-base font-extrabold text-gray-900">{selectedRoomName}</Text><Text className="text-xs text-emerald-600 mt-0.5">채팅방</Text></View>
                </View>
                <ScrollView ref={scrollRef} className="flex-1 bg-[#FBFDFD]" contentContainerStyle={{ padding: 16 }} onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}>
                  {messagesQuery.isLoading ? <ActivityIndicator color={BRAND} className="mt-8" /> : (messagesQuery.data ?? []).map((message) => {
                    const mine = message.sender_id === userId;
                    return <View key={message.id} className={`mb-3 ${mine ? "items-end" : "items-start"}`}><View className={`max-w-[78%] rounded-2xl px-3 py-2 ${mine ? "bg-cyan-700" : "bg-white border border-gray-200"}`}><Text className={mine ? "text-white" : "text-gray-800"}>{message.content}</Text></View><Text className="text-[10px] text-gray-400 mt-1">{formatTime(message.created_at)}</Text></View>;
                  })}
                </ScrollView>
                <View className="p-3 border-t border-gray-100 flex-row items-end"><TextInput value={draft} onChangeText={setDraft} onSubmitEditing={send} placeholder="메시지 입력" placeholderTextColor="#94A3B8" className="flex-1 min-h-11 max-h-28 px-4 py-2 rounded-2xl bg-gray-100 text-gray-900" multiline /><Pressable onPress={send} disabled={!draft.trim() || sendMutation.isPending} className="ml-2 w-11 h-11 rounded-2xl items-center justify-center disabled:opacity-40" style={{ backgroundColor: BRAND }}>{sendMutation.isPending ? <ActivityIndicator color="white" /> : <Send size={18} color="white" />}</Pressable></View>
                {!!sendError && <Text className="px-4 pb-2 text-xs text-red-600">{sendError}</Text>}
              </> : <View className="flex-1 items-center justify-center px-8"><Users size={42} color="#CBD5E1" /><Text className="text-base font-bold text-gray-500 mt-4">채팅방을 선택하세요.</Text></View>}
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </AppScreenLayout>
  );
};

function getRoomName(room: ChatRoom | null, currentUserId?: number) {
  if (!room) return "채팅";
  if (room.name) return room.name;
  const names = room.participants
    .filter((participant) => participant.user_id !== currentUserId)
    .map((participant) => participant.user?.name)
    .filter((name): name is string => !!name);
  return names.join(", ") || "채팅방";
}
