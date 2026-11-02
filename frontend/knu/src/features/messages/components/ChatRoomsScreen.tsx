import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { useIsFocused } from "@react-navigation/native";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { ArrowLeft, Bell, BellOff, Check, Pencil, Plus, Send, Trash2, Users, X } from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { KeyboardAwareContent } from "@/components/ui/KeyboardAwareContent";
import { getAxiosErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { chatApi } from "@/features/chat/api/chat-api";
import { UnreadCountBadge } from "@/features/chat/components/UnreadCountBadge";
import { presenceApi } from "@/features/presence/api/presence-api";
import type { ChatRoom } from "@/features/chat/types";
import { usePresenceStore } from "@/features/presence/store/presence-store";
import { getFriends } from "@/features/friend/api/friend";
import type { FriendUser } from "@/features/friend/api/types";

const BRAND = "#13708D";

const formatTime = (value: string) =>
  new Date(value).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });

export const ChatRoomsScreen = () => {
  const isFocused = useIsFocused();
  const { friendId, roomId } = useLocalSearchParams<{ friendId?: string; roomId?: string }>();
  const requestedFriendId = Number(friendId);
  const requestedRoomId = Number(roomId);
  const userId = useAuthStore((state) => state.user?.id);
  const setActiveRoomId = usePresenceStore((state) => state.setActiveRoomId);
  const client = useQueryClient();
  const { width } = useWindowDimensions();
  const isWide = width >= 760;
  const [selectedRoom, setSelectedRoom] = useState<ChatRoom | null>(null);
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [newChatModalVisible, setNewChatModalVisible] = useState(false);
  const [selectedFriendIds, setSelectedFriendIds] = useState<number[]>([]);
  const [newRoomName, setNewRoomName] = useState("");
  const [newChatError, setNewChatError] = useState<string | null>(null);
  const [settingsRoom, setSettingsRoom] = useState<ChatRoom | null>(null);
  const [roomNameDraft, setRoomNameDraft] = useState("");
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const roomsQuery = useQuery({
    queryKey: ["chatRooms", userId],
    queryFn: async () => (await chatApi.getRooms()).data,
    enabled: !!userId,
    refetchInterval: 10_000,
  });

  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: getFriends,
    enabled: newChatModalVisible,
  });

  const createDirectRoom = useMutation({
    mutationFn: async (targetUserId: number) => (await chatApi.createRoom({ friend_id: targetUserId })).data,
    onSuccess: (room) => {
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
      setSelectedRoom(room);
    },
  });

  const createRoomMutation = useMutation({
    mutationFn: async ({ friendIds, name }: { friendIds: number[]; name?: string }) =>
      (await chatApi.createRoom({ participant_ids: friendIds, name })).data,
    onSuccess: (room) => {
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
      setSelectedRoom(room);
      setNewChatModalVisible(false);
      setSelectedFriendIds([]);
      setNewRoomName("");
      setNewChatError(null);
    },
    onError: (error) => setNewChatError(getAxiosErrorMessage(error, "채팅방을 만들지 못했습니다.")),
  });

  useEffect(() => {
    if (!Number.isInteger(requestedFriendId) || requestedFriendId <= 0 || createDirectRoom.isPending) return;
    createDirectRoom.mutate(requestedFriendId);
  }, [requestedFriendId]);

  useEffect(() => {
    if (!Number.isInteger(requestedRoomId) || requestedRoomId <= 0) return;

    const room = roomsQuery.data?.find((item) => item.id === requestedRoomId);
    if (room) {
      setSelectedRoom(room);
    }
  }, [requestedRoomId, roomsQuery.data]);

  const messagesQuery = useQuery({
    queryKey: ["chatMessages", selectedRoom?.id],
    queryFn: async () => (await chatApi.getMessages(selectedRoom!.id)).data,
    enabled: isFocused && !!selectedRoom,
    refetchInterval: 5_000,
  });

  useEffect(() => {
    if (!selectedRoom || !messagesQuery.isSuccess) return;

    client.setQueryData<ChatRoom[]>(["chatRooms", userId], (current) => current?.map((room) => (
      room.id === selectedRoom.id ? { ...room, unread_count: 0 } : room
    )));
  }, [client, messagesQuery.dataUpdatedAt, messagesQuery.isSuccess, selectedRoom?.id]);

  useFocusEffect(useCallback(() => {
    const activeRoomId = selectedRoom?.id ?? null;
    setActiveRoomId(activeRoomId);
    // 사용자가 채팅방 접속 시 푸시 알람 차단
    if (!userId) return;
    void presenceApi.updateMyPresence({
      active_room_id: activeRoomId,
      is_app_foreground: true,
    }).catch(() => undefined);
    return () => {
      setActiveRoomId(null);
      void presenceApi.updateMyPresence({
        active_room_id: null,
        is_app_foreground: true,
      }).catch(() => undefined);
    };
  }, [selectedRoom?.id, setActiveRoomId, userId]));

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

  const updateRoomMutation = useMutation({
    mutationFn: async ({ roomId, name }: { roomId: number; name: string }) =>
      (await chatApi.updateRoom(roomId, { name })).data,
    onSuccess: (room) => {
      setSelectedRoom((current) => current?.id === room.id ? room : current);
      setSettingsRoom(room);
      setSettingsError(null);
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
    },
    onError: (error) => setSettingsError(getAxiosErrorMessage(error, "채팅방 이름을 변경하지 못했습니다.")),
  });

  const updateRoomNotificationMutation = useMutation({
    mutationFn: async ({ roomId, isMuted }: { roomId: number; isMuted: boolean }) =>
      (await chatApi.updateRoomNotification(roomId, { is_muted: isMuted })).data,
    onSuccess: (response) => {
      const applyMute = (room: ChatRoom) => room.id === response.room_id
        ? { ...room, is_muted: response.is_muted }
        : room;
      setSelectedRoom((current) => current ? applyMute(current) : current);
      setSettingsRoom((current) => current ? applyMute(current) : current);
      client.setQueryData<ChatRoom[]>(["chatRooms", userId], (current) => current?.map(applyMute));
      setSettingsError(null);
    },
    onError: (error) => setSettingsError(getAxiosErrorMessage(error, "알림 설정을 변경하지 못했습니다.")),
  });

  const deleteRoomMutation = useMutation({
    mutationFn: async (roomId: number) => chatApi.deleteRoom(roomId),
    onSuccess: (_, roomId) => {
      if (selectedRoom?.id === roomId) setSelectedRoom(null);
      setSettingsRoom(null);
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
    },
    onError: (error) => setSettingsError(getAxiosErrorMessage(error, "채팅방에서 나가지 못했습니다.")),
  });

  const rooms = roomsQuery.data ?? [];
  const selectedRoomName = useMemo(() => getRoomName(selectedRoom, userId), [selectedRoom, userId]);
  const showConversation = isWide || !!selectedRoom;

  const send = () => {
    const content = draft.trim();
    if (!content || sendMutation.isPending || !selectedRoom) return;
    sendMutation.mutate(content);
  };

  const toggleFriend = (friendId: number) => {
    setSelectedFriendIds((current) => current.includes(friendId)
      ? current.filter((id) => id !== friendId)
      : [...current, friendId]);
  };

  const openNewChat = () => {
    setSelectedFriendIds([]);
    setNewRoomName("");
    setNewChatError(null);
    setNewChatModalVisible(true);
  };

  const createSelectedRoom = () => {
    if (selectedFriendIds.length === 0 || createRoomMutation.isPending) return;
    const isGroup = selectedFriendIds.length >= 2;
    createRoomMutation.mutate({
      friendIds: selectedFriendIds,
      name: isGroup ? newRoomName.trim() || undefined : undefined,
    });
  };

  const openSettings = (room: ChatRoom) => {
    setSettingsRoom(room);
    setRoomNameDraft(room.name ?? "");
    setSettingsError(null);
  };

  const leaveRoom = () => {
    if (!settingsRoom || deleteRoomMutation.isPending) return;
    Alert.alert(
      settingsRoom.is_group ? "단체 채팅방 나가기" : "채팅방 삭제",
      settingsRoom.is_group ? "이 채팅방에서 나가시겠어요?" : "이 대화방에서 나가시겠어요?",
      [
        { text: "취소", style: "cancel" },
        { text: settingsRoom.is_group ? "나가기" : "삭제", style: "destructive", onPress: () => deleteRoomMutation.mutate(settingsRoom.id) },
      ],
    );
  };

  return (
    <AppScreenLayout>
      <KeyboardAwareContent>
        <View className="flex-1 p-3" style={{ gap: 12, flexDirection: isWide ? "row" : "column", minHeight: 0 }}>
          {(!showConversation || isWide) && (
            <View className="bg-white rounded-[28px] border border-gray-200 overflow-hidden" style={{ width: isWide ? "38%" : "100%" }}>
              <View className="px-5 pt-5 pb-4 border-b border-gray-100 flex-row items-center">
                <View className="flex-1">
                  <Text className="text-2xl font-extrabold text-gray-900">채팅</Text>
                  <Text className="text-sm text-gray-400 mt-1">친구와 개인·단체 대화를 시작하세요.</Text>
                </View>
                <Pressable
                  accessibilityLabel="새 채팅 만들기"
                  onPress={openNewChat}
                  className="w-11 h-11 rounded-2xl bg-cyan-700 items-center justify-center active:opacity-80"
                >
                  <Plus size={23} color="white" />
                </Pressable>
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
                  <Text className="text-base font-extrabold text-gray-800 mt-4">아직 대화가 없습니다.</Text>
                  <Text className="text-xs text-gray-400 text-center mt-2">친구 화면에서 친구를 선택해 대화를 시작하세요.</Text>
                </View>
              ) : (
                <ScrollView contentContainerStyle={{ padding: 10 }} showsVerticalScrollIndicator={false}>
                  {rooms.map((room) => {
                    const active = selectedRoom?.id === room.id;
                    const name = getRoomName(room, userId);
                    return <Pressable key={room.id} onPress={() => setSelectedRoom(room)} onLongPress={() => openSettings(room)} delayLongPress={450} className={`p-4 rounded-2xl mb-1 flex-row items-center ${active ? "bg-cyan-50" : "active:bg-gray-50"}`}>
                      <View className="w-11 h-11 rounded-full bg-cyan-100 items-center justify-center">
                        <Text className="font-extrabold" style={{ color: BRAND }}>{name.slice(0, 1)}</Text>
                      </View>
                      <View className="flex-1 ml-3">
                        <Text className="text-[15px] font-extrabold text-gray-900" numberOfLines={1}>{name}</Text>
                        <Text className="text-xs text-gray-400 mt-1">
                          {room.is_group ? "그룹 채팅" : "개인 채팅"}{room.is_muted ? " · 알림 꺼짐" : ""}
                        </Text>
                      </View>
                      <UnreadCountBadge count={room.unread_count} size="room" />
                    </Pressable>;
                  })}
                </ScrollView>
              )}
            </View>
          )}

          {showConversation && (
            <View className="flex-1 bg-white rounded-[28px] border border-gray-200 overflow-hidden" style={{ minHeight: 0 }}>
              {selectedRoom ? <>
                <View className="h-[72px] px-4 border-b border-gray-100 flex-row items-center">
                  {!isWide && <Pressable onPress={() => setSelectedRoom(null)} className="w-10 h-10 rounded-full items-center justify-center mr-1"><ArrowLeft size={22} color="#334155" /></Pressable>}
                  <View className="w-10 h-10 rounded-full bg-cyan-100 items-center justify-center"><Text className="font-extrabold" style={{ color: BRAND }}>{selectedRoomName.slice(0, 1)}</Text></View>
                  <View className="flex-1 ml-3"><Text className="text-base font-extrabold text-gray-900">{selectedRoomName}</Text><Text className="text-xs text-emerald-600 mt-0.5">채팅방</Text></View>
                </View>
                <ScrollView ref={scrollRef} className="flex-1 bg-[#FBFDFD]" contentContainerStyle={{ padding: 16 }} keyboardShouldPersistTaps="handled" onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}>
                  {messagesQuery.isLoading ? <ActivityIndicator color={BRAND} className="mt-8" /> : (messagesQuery.data ?? []).map((message) => {
                    const mine = message.sender_id === userId;
                    const senderName = getParticipantName(selectedRoom, message.sender_id);
                    const showSenderProfile = selectedRoom.is_group && !mine;
                    return <View key={message.id} className={`mb-3 flex-row ${mine ? "justify-end" : "justify-start"}`}>
                      {showSenderProfile && <View className="w-9 h-9 mt-5 mr-2 rounded-full bg-cyan-100 items-center justify-center"><Text className="font-extrabold" style={{ color: BRAND }}>{getProfileInitial(senderName)}</Text></View>}
                      <View className={`max-w-[78%] ${mine ? "items-end" : "items-start"}`}>
                        {showSenderProfile && <Text className="mb-1 text-xs font-bold text-gray-500">{senderName}</Text>}
                        <View className={`rounded-2xl px-3 py-2 ${mine ? "bg-cyan-700" : "bg-white border border-gray-200"}`}><Text className={mine ? "text-white" : "text-gray-800"}>{message.content}</Text></View>
                        <View className="flex-row items-center mt-1" style={{ gap: 4 }}>
                          {mine && message.unread_count > 0 && (
                            <Text className="text-[10px] font-bold text-amber-600" accessibilityLabel={`읽지 않은 사람 ${message.unread_count}명`}>
                              {message.unread_count}
                            </Text>
                          )}
                          <Text className="text-[10px] text-gray-400">{formatTime(message.created_at)}</Text>
                        </View>
                      </View>
                    </View>;
                  })}
                </ScrollView>
                <View className="p-3 border-t border-gray-100 flex-row items-end"><TextInput value={draft} onChangeText={setDraft} onSubmitEditing={send} placeholder="메시지 입력" placeholderTextColor="#94A3B8" className="flex-1 min-h-11 max-h-28 px-4 py-2 rounded-2xl bg-gray-100 text-gray-900" multiline /><Pressable onPress={send} disabled={!draft.trim() || sendMutation.isPending} className="ml-2 w-11 h-11 rounded-2xl items-center justify-center disabled:opacity-40" style={{ backgroundColor: BRAND }}>{sendMutation.isPending ? <ActivityIndicator color="white" /> : <Send size={18} color="white" />}</Pressable></View>
                {!!sendError && <Text className="px-4 pb-2 text-xs text-red-600">{sendError}</Text>}
              </> : <View className="flex-1 items-center justify-center px-8"><Users size={42} color="#CBD5E1" /><Text className="text-base font-bold text-gray-500 mt-4">채팅방을 선택하세요.</Text></View>}
            </View>
          )}
        </View>
      </KeyboardAwareContent>

      <Modal
        visible={newChatModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setNewChatModalVisible(false)}
      >
        <Pressable className="flex-1 bg-black/45 items-center justify-center px-5" onPress={() => setNewChatModalVisible(false)}>
          <Pressable className="w-full max-w-md max-h-[82%] rounded-3xl bg-white p-5" onPress={(event) => event.stopPropagation()}>
            <View className="flex-row items-center justify-between">
              <View>
                <Text className="text-xl font-extrabold text-gray-900">새 채팅</Text>
                <Text className="text-xs text-gray-400 mt-1">친구 1명은 개인 채팅, 2명 이상은 단체 채팅입니다.</Text>
              </View>
              <Pressable onPress={() => setNewChatModalVisible(false)} className="w-9 h-9 rounded-full bg-gray-100 items-center justify-center"><X size={19} color="#475569" /></Pressable>
            </View>

            <ScrollView className="mt-4" contentContainerStyle={{ paddingBottom: 4 }}>
              {friendsQuery.isLoading ? <ActivityIndicator color={BRAND} className="my-8" /> : (friendsQuery.data ?? []).length === 0 ? (
                <Text className="py-8 text-center text-sm text-gray-400">선택할 친구가 없습니다.</Text>
              ) : (friendsQuery.data ?? []).map((friend: FriendUser) => {
                const selected = selectedFriendIds.includes(friend.id);
                return <Pressable key={friend.id} onPress={() => toggleFriend(friend.id)} className={`py-3 px-2 rounded-2xl flex-row items-center ${selected ? "bg-cyan-50" : "active:bg-gray-50"}`}>
                  <View className="w-10 h-10 rounded-full bg-cyan-100 items-center justify-center"><Text className="font-extrabold" style={{ color: BRAND }}>{friend.name.slice(0, 1)}</Text></View>
                  <View className="flex-1 ml-3"><Text className="font-bold text-gray-900">{friend.name}</Text><Text className="text-xs text-gray-400 mt-0.5">{[friend.department, friend.student_id].filter(Boolean).join(" · ") || "강남대학교"}</Text></View>
                  <View className={`w-6 h-6 rounded-full border items-center justify-center ${selected ? "bg-cyan-700 border-cyan-700" : "border-gray-300"}`}>{selected && <Check size={15} color="white" />}</View>
                </Pressable>;
              })}
            </ScrollView>

            {selectedFriendIds.length >= 2 && <TextInput value={newRoomName} onChangeText={setNewRoomName} placeholder="단체 채팅방 이름 (선택)" placeholderTextColor="#94A3B8" className="mt-3 h-12 px-4 rounded-2xl bg-gray-100 text-gray-900" maxLength={100} />}
            {!!newChatError && <Text className="mt-3 text-xs text-red-600">{newChatError}</Text>}
            <Pressable onPress={createSelectedRoom} disabled={selectedFriendIds.length === 0 || createRoomMutation.isPending} className="mt-4 h-12 rounded-2xl items-center justify-center disabled:opacity-40" style={{ backgroundColor: BRAND }}>
              {createRoomMutation.isPending ? <ActivityIndicator color="white" /> : <Text className="font-extrabold text-white">{selectedFriendIds.length >= 2 ? "단체 채팅 만들기" : "대화 시작"}</Text>}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>

      <Modal
        visible={!!settingsRoom}
        transparent
        animationType="fade"
        onRequestClose={() => setSettingsRoom(null)}
      >
        <Pressable className="flex-1 bg-black/45 items-center justify-center px-5" onPress={() => setSettingsRoom(null)}>
          <Pressable className="w-full max-w-md rounded-3xl bg-white p-5" onPress={(event) => event.stopPropagation()}>
            <View className="flex-row items-center justify-between">
              <View className="flex-1 pr-3"><Text className="text-xl font-extrabold text-gray-900" numberOfLines={1}>{getRoomName(settingsRoom, userId)}</Text><Text className="text-xs text-gray-400 mt-1">채팅방을 길게 눌러 열었습니다.</Text></View>
              <Pressable onPress={() => setSettingsRoom(null)} className="w-9 h-9 rounded-full bg-gray-100 items-center justify-center"><X size={19} color="#475569" /></Pressable>
            </View>

            {settingsRoom?.is_group ? <>
              <Text className="mt-5 text-xs font-bold text-gray-500">채팅방 이름</Text>
              <View className="mt-2 flex-row items-center"><TextInput value={roomNameDraft} onChangeText={setRoomNameDraft} placeholder="채팅방 이름" placeholderTextColor="#94A3B8" className="flex-1 h-12 px-4 rounded-2xl bg-gray-100 text-gray-900" maxLength={100} /><Pressable onPress={() => settingsRoom && updateRoomMutation.mutate({ roomId: settingsRoom.id, name: roomNameDraft })} disabled={!roomNameDraft.trim() || updateRoomMutation.isPending} className="ml-2 h-12 px-4 rounded-2xl bg-cyan-700 items-center justify-center disabled:opacity-40">{updateRoomMutation.isPending ? <ActivityIndicator color="white" /> : <Pencil size={18} color="white" />}</Pressable></View>
            </> : <Text className="mt-5 text-xs text-gray-400">개인 채팅방 이름은 상대방 이름으로 표시됩니다.</Text>}

            <Pressable onPress={() => settingsRoom && updateRoomNotificationMutation.mutate({ roomId: settingsRoom.id, isMuted: !settingsRoom.is_muted })} disabled={updateRoomNotificationMutation.isPending} className="mt-5 h-13 px-4 rounded-2xl bg-gray-100 flex-row items-center disabled:opacity-40">
              {settingsRoom?.is_muted ? <Bell size={19} color={BRAND} /> : <BellOff size={19} color="#475569" />}<Text className="ml-3 font-bold text-gray-800">{settingsRoom?.is_muted ? "알림 켜기" : "알림 차단"}</Text>
            </Pressable>
            <Pressable onPress={leaveRoom} disabled={deleteRoomMutation.isPending} className="mt-2 h-13 px-4 rounded-2xl bg-rose-50 flex-row items-center disabled:opacity-40">
              <Trash2 size={19} color="#E11D48" /><Text className="ml-3 font-bold text-rose-600">{settingsRoom?.is_group ? "채팅방 나가기" : "채팅방 삭제"}</Text>
            </Pressable>
            {!!settingsError && <Text className="mt-3 text-xs text-red-600">{settingsError}</Text>}
          </Pressable>
        </Pressable>
      </Modal>
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

function getParticipantName(room: ChatRoom, userId: number) {
  return room.participants.find((participant) => participant.user_id === userId)?.user?.name ?? "알 수 없음";
}

function getProfileInitial(name: string) {
  return name.trim().slice(0, 1) || "?";
}
