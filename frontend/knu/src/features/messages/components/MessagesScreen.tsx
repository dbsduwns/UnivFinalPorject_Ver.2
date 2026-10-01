import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import {
  ArrowLeft,
  CalendarDays,
  ChevronRight,
  MessageCircle,
  Search,
  Send,
  UserPlus,
  Users,
  X,
} from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { getAxiosErrorMessage } from "@/api/errors";
import { chatApi } from "@/features/chat/api/chat-api";
import type { ChatMessage } from "@/features/chat/types";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { FriendInviteModal } from "@/features/friend/components/FriendInviteModal";
import { FriendTimetableModal } from "@/features/friend/components/FriendTimetableModal";
import { getFriendRequests, getFriends } from "@/features/friend/api/friend";
import type { FriendUser } from "@/features/friend/api/types";

const BRAND = "#13708D";

const getInitial = (name: string) => name.trim().slice(0, 1) || "친";
const messageTime = (value: string) =>
  new Date(value).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });

const FriendAvatar = ({ friend, size = 48 }: { friend: FriendUser; size?: number }) => (
  <View
    className="items-center justify-center bg-cyan-50 border border-cyan-100"
    style={{ width: size, height: size, borderRadius: size / 2 }}
  >
    <Text style={{ color: BRAND, fontSize: size * 0.36, fontWeight: "800" }}>
      {getInitial(friend.name)}
    </Text>
  </View>
);

export const MessagesScreen = () => {
  const userId = useAuthStore((state) => state.user?.id);
  const queryClient = useQueryClient();
  const { width } = useWindowDimensions();
  const isWide = width >= 760;
  const [query, setQuery] = useState("");
  const [selectedFriend, setSelectedFriend] = useState<FriendUser | null>(null);
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [refreshingMessages, setRefreshingMessages] = useState(false);
  const conversationScrollRef = useRef<ScrollView>(null);
  const shouldAutoScrollRef = useRef(true);
  const [inviteModalVisible, setInviteModalVisible] = useState(false);
  const [timetableFriend, setTimetableFriend] = useState<FriendUser | null>(null);

  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: getFriends,
  });
  const requestsQuery = useQuery({
    queryKey: ["friendRequests"],
    queryFn: getFriendRequests,
  });

  const roomQuery = useQuery({
    queryKey: ["directChatRoom", userId, selectedFriend?.id],
    queryFn: async () => (await chatApi.createRoom({ friend_id: selectedFriend!.id })).data,
    enabled: !!userId && !!selectedFriend,
    staleTime: 60_000,
  });
  const roomId = roomQuery.data?.id;
  const messagesQuery = useQuery({
    queryKey: ["chatMessages", userId, roomId],
    queryFn: async () => (await chatApi.getMessages(roomId!)).data,
    enabled: !!userId && roomId !== undefined,
    refetchInterval: 5000,
  });
  const sendMutation = useMutation({
    mutationFn: ({ targetRoomId, content }: { targetRoomId: number; targetFriendId: number; content: string }) =>
      chatApi.sendMessage(targetRoomId, content),
    onSuccess: ({ data }, { targetRoomId, targetFriendId, content }) => {
      shouldAutoScrollRef.current = true;
      queryClient.setQueryData<ChatMessage[]>(
        ["chatMessages", userId, targetRoomId],
        (previous) => previous?.some((message) => message.id === data.message.id)
          ? previous
          : [...(previous ?? []), data.message]
      );
      if (selectedFriend?.id === targetFriendId) {
        setDraft((current) => current.trim() === content ? "" : current);
        setSendError(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["chatMessages", userId, targetRoomId] });
    },
    onError: (error, { targetFriendId }) => {
      if (selectedFriend?.id === targetFriendId) {
        setSendError(getAxiosErrorMessage(error, "메시지를 보내지 못했어요."));
      }
    },
  });

  const selectFriend = (friend: FriendUser) => {
    setSelectedFriend(friend);
    setDraft("");
    setSendError(null);
    shouldAutoScrollRef.current = true;
  };

  const sendMessage = () => {
    const content = draft.trim();
    if (!roomId || !selectedFriend || !content || sendMutation.isPending) return;
    setSendError(null);
    sendMutation.mutate({ targetRoomId: roomId, targetFriendId: selectedFriend.id, content });
  };

  const friends = friendsQuery.data;
  const pendingCount = requestsQuery.data?.received?.length ?? 0;
  const filteredFriends = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("ko");
    const friendList = friends ?? [];
    if (!keyword) return friendList;

    return friendList.filter((friend) =>
      [friend.name, friend.department, friend.student_id]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase("ko").includes(keyword))
    );
  }, [friends, query]);

  const isRefreshing = friendsQuery.isRefetching || requestsQuery.isRefetching;
  const refresh = () => {
    void Promise.all([friendsQuery.refetch(), requestsQuery.refetch()]);
  };

  const showList = isWide || !selectedFriend;
  const showConversation = isWide || !!selectedFriend;

  return (
    <AppScreenLayout>
      <View className="flex-1 bg-[#F4F7F8] px-4 pb-4 pt-3 md:px-7 md:pb-7">
        <View className="self-center w-full max-w-[1080px] flex-1">
          <View className="flex-row items-center justify-between mb-4">
            <View>
              <Text className="text-2xl font-extrabold text-gray-900">쪽지</Text>
              <Text className="text-sm text-gray-500 mt-1">친구를 선택해 대화를 시작해보세요.</Text>
            </View>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="친구 초대"
              onPress={() => setInviteModalVisible(true)}
              className="h-11 px-4 rounded-2xl bg-white border border-gray-200 flex-row items-center shadow-sm active:bg-gray-50"
            >
              <UserPlus size={18} color={BRAND} />
              <Text className="ml-2 font-bold" style={{ color: BRAND }}>
                친구 초대
              </Text>
              {pendingCount > 0 && (
                <View className="ml-2 min-w-5 h-5 px-1 rounded-full bg-rose-500 items-center justify-center">
                  <Text className="text-[10px] text-white font-extrabold">{pendingCount}</Text>
                </View>
              )}
            </Pressable>
          </View>

          <View className={`flex-1 ${isWide ? "flex-row" : ""}`} style={{ gap: 14 }}>
            {showList && (
              <View
                className="bg-white rounded-[28px] border border-gray-200 overflow-hidden"
                style={isWide ? { width: 350 } : { flex: 1 }}
              >
                <View className="px-4 pt-4 pb-3 border-b border-gray-100">
                  <View className="flex-row items-center rounded-2xl bg-gray-100 px-3 h-11">
                    <Search size={18} color="#94A3B8" />
                    <TextInput
                      value={query}
                      onChangeText={setQuery}
                      placeholder="이름, 학과, 학번 검색"
                      placeholderTextColor="#94A3B8"
                      className="flex-1 ml-2 text-sm text-gray-900"
                    />
                    {!!query && (
                      <Pressable onPress={() => setQuery("")} className="p-1">
                        <X size={16} color="#94A3B8" />
                      </Pressable>
                    )}
                  </View>
                </View>

                {pendingCount > 0 && (
                  <Pressable
                    onPress={() => setInviteModalVisible(true)}
                    className="mx-4 mt-4 px-4 py-3 rounded-2xl bg-amber-50 border border-amber-100 flex-row items-center"
                  >
                    <View className="w-9 h-9 rounded-full bg-amber-100 items-center justify-center">
                      <UserPlus size={17} color="#B45309" />
                    </View>
                    <View className="flex-1 ml-3">
                      <Text className="text-sm font-bold text-amber-900">새 친구 요청 {pendingCount}개</Text>
                      <Text className="text-xs text-amber-700 mt-0.5">요청을 확인하고 수락해보세요.</Text>
                    </View>
                    <ChevronRight size={17} color="#B45309" />
                  </Pressable>
                )}

                <View className="px-5 pt-4 pb-2 flex-row items-center justify-between">
                  <Text className="text-xs font-extrabold text-gray-500 tracking-wider">친구 목록</Text>
                  <Text className="text-xs font-bold text-gray-400">{filteredFriends.length}명</Text>
                </View>

                {friendsQuery.isLoading ? (
                  <View className="flex-1 items-center justify-center">
                    <ActivityIndicator color={BRAND} />
                    <Text className="text-xs text-gray-400 mt-3">친구 목록을 불러오는 중이에요.</Text>
                  </View>
                ) : friendsQuery.isError ? (
                  <View className="flex-1 items-center justify-center px-8">
                    <Users size={42} color="#CBD5E1" />
                    <Text className="text-sm font-bold text-gray-700 mt-4">친구 목록을 불러오지 못했어요.</Text>
                    <Pressable onPress={refresh} className="mt-4 px-4 py-2 rounded-xl bg-cyan-50">
                      <Text className="text-sm font-bold" style={{ color: BRAND }}>다시 시도</Text>
                    </Pressable>
                  </View>
                ) : filteredFriends.length === 0 ? (
                  <View className="flex-1 items-center justify-center px-8">
                    <View className="w-16 h-16 rounded-full bg-cyan-50 items-center justify-center">
                      {query ? <Search size={28} color={BRAND} /> : <UserPlus size={28} color={BRAND} />}
                    </View>
                    <Text className="text-base font-extrabold text-gray-800 mt-4">
                      {query ? "검색 결과가 없어요" : "아직 등록된 친구가 없어요"}
                    </Text>
                    <Text className="text-xs leading-5 text-gray-400 text-center mt-2">
                      {query
                        ? "다른 이름이나 학번으로 검색해보세요."
                        : "친구 초대에서 아이디, 이메일 또는 초대 링크로 친구를 초대해보세요."}
                    </Text>
                    {!query && (
                      <Pressable
                        onPress={() => setInviteModalVisible(true)}
                        className="mt-5 px-5 py-3 rounded-2xl flex-row items-center"
                        style={{ backgroundColor: BRAND }}
                      >
                        <UserPlus size={17} color="white" />
                        <Text className="text-white font-bold ml-2">친구 추가하기</Text>
                      </Pressable>
                    )}
                  </View>
                ) : (
                  <ScrollView
                    className="flex-1"
                    contentContainerStyle={{ paddingHorizontal: 10, paddingBottom: 12 }}
                    refreshControl={
                      <RefreshControl refreshing={isRefreshing} onRefresh={refresh} tintColor={BRAND} />
                    }
                    showsVerticalScrollIndicator={false}
                  >
                    {filteredFriends.map((friend) => {
                      const selected = selectedFriend?.id === friend.id;

                      return (
                        <View
                          key={friend.id}
                          className={`px-3 py-3 rounded-2xl flex-row items-center mb-1 ${
                            selected ? "bg-cyan-50" : "active:bg-gray-50"
                          }`}
                        >
                          <FriendAvatar friend={friend} />
                          <View className="flex-1 ml-3">
                            <Text className="text-[15px] font-extrabold text-gray-900" numberOfLines={1}>
                              {friend.name}
                            </Text>
                            <Text className="text-xs text-gray-400 mt-1" numberOfLines={1}>
                              {[friend.department, friend.student_id].filter(Boolean).join(" · ") || "강남대학교"}
                            </Text>
                          </View>
                          <View className="flex-row items-center ml-2" style={{ gap: 6 }}>
                            <Pressable
                              accessibilityLabel={`${friend.name}에게 쪽지 보내기`}
                              onPress={() => selectFriend(friend)}
                              className={`h-9 px-2.5 rounded-xl flex-row items-center ${
                                selected ? "bg-cyan-700" : "bg-cyan-50"
                              }`}
                            >
                              <MessageCircle size={15} color={selected ? "white" : BRAND} />
                              <Text
                                className={`ml-1 text-[11px] font-extrabold ${selected ? "text-white" : "text-cyan-800"}`}
                              >
                                쪽지
                              </Text>
                            </Pressable>
                            <Pressable
                              accessibilityLabel={`${friend.name} 시간표 보기`}
                              onPress={() => setTimetableFriend(friend)}
                              className="h-9 px-2.5 rounded-xl bg-gray-100 flex-row items-center"
                            >
                              <CalendarDays size={15} color="#64748B" />
                              <Text className="ml-1 text-[11px] font-extrabold text-gray-600">시간표</Text>
                            </Pressable>
                          </View>
                        </View>
                      );
                    })}
                  </ScrollView>
                )}
              </View>
            )}

            {showConversation && (
              <View className="flex-1 bg-white rounded-[28px] border border-gray-200 overflow-hidden">
                {selectedFriend ? (
                  <>
                    <View className="h-[72px] px-4 border-b border-gray-100 flex-row items-center">
                      {!isWide && (
                        <Pressable
                          accessibilityLabel="친구 목록으로 돌아가기"
                          onPress={() => {
                            setSelectedFriend(null);
                            setDraft("");
                          }}
                          className="w-10 h-10 rounded-full items-center justify-center mr-1 active:bg-gray-100"
                        >
                          <ArrowLeft size={22} color="#334155" />
                        </Pressable>
                      )}
                      <FriendAvatar friend={selectedFriend} size={42} />
                      <View className="flex-1 ml-3">
                        <Text className="text-base font-extrabold text-gray-900">{selectedFriend.name}</Text>
                        <Text className="text-xs text-emerald-600 mt-0.5">친구</Text>
                      </View>
                      <Pressable
                        accessibilityLabel="친구 시간표 보기"
                        onPress={() => setTimetableFriend(selectedFriend)}
                        className="h-10 px-3 rounded-xl bg-cyan-50 flex-row items-center active:bg-cyan-100"
                      >
                        <CalendarDays size={17} color={BRAND} />
                        <Text className="ml-1.5 text-xs font-bold" style={{ color: BRAND }}>시간표</Text>
                      </Pressable>
                    </View>

                    {roomQuery.isPending || (roomId && messagesQuery.isPending) ? (
                      <View className="flex-1 items-center justify-center bg-[#FBFDFD]">
                        <ActivityIndicator color={BRAND} />
                        <Text className="text-sm text-gray-500 mt-3">대화를 불러오는 중이에요.</Text>
                      </View>
                    ) : roomQuery.isError || (messagesQuery.isError && !messagesQuery.data) ? (
                      <View className="flex-1 items-center justify-center px-8 bg-[#FBFDFD]">
                        <Text className="text-sm text-gray-600 text-center">
                          {getAxiosErrorMessage(roomQuery.error ?? messagesQuery.error, "대화를 불러오지 못했어요.")}
                        </Text>
                        <Pressable
                          onPress={() => {
                            if (roomQuery.isError) void roomQuery.refetch();
                            else void messagesQuery.refetch();
                          }}
                          className="mt-4 px-4 py-2 rounded-xl bg-cyan-50"
                        >
                          <Text className="font-bold" style={{ color: BRAND }}>다시 시도</Text>
                        </Pressable>
                      </View>
                    ) : (
                      <ScrollView
                        ref={conversationScrollRef}
                        className="flex-1 bg-[#FBFDFD]"
                        contentContainerStyle={{ flexGrow: 1, padding: 16 }}
                        keyboardShouldPersistTaps="handled"
                        onScroll={({ nativeEvent }) => {
                          const { contentOffset, contentSize, layoutMeasurement } = nativeEvent;
                          shouldAutoScrollRef.current =
                            contentOffset.y + layoutMeasurement.height >= contentSize.height - 60;
                        }}
                        scrollEventThrottle={100}
                        onContentSizeChange={() => {
                          if (shouldAutoScrollRef.current) {
                            conversationScrollRef.current?.scrollToEnd({ animated: false });
                          }
                        }}
                        refreshControl={
                          <RefreshControl
                            refreshing={refreshingMessages}
                            onRefresh={() => {
                              setRefreshingMessages(true);
                              void messagesQuery.refetch().finally(() => setRefreshingMessages(false));
                            }}
                            tintColor={BRAND}
                          />
                        }
                      >
                        {(messagesQuery.data ?? []).length === 0 ? (
                          <View className="flex-1 items-center justify-center px-4">
                            <View className="w-20 h-20 rounded-full bg-cyan-50 items-center justify-center">
                              <MessageCircle size={36} color={BRAND} />
                            </View>
                            <Text className="text-lg font-extrabold text-gray-800 mt-5">
                              {selectedFriend.name} 님과의 대화
                            </Text>
                            <Text className="text-sm leading-6 text-gray-400 text-center mt-2">
                              아직 주고받은 쪽지가 없어요.{"\n"}첫 메시지를 보내보세요.
                            </Text>
                          </View>
                        ) : (
                          messagesQuery.data?.map((message) => {
                            const mine = message.sender_id === userId;
                            return (
                              <View
                                key={message.id}
                                className={`mb-3 flex-row items-end ${mine ? "justify-end" : "justify-start"}`}
                              >
                                {!mine && <FriendAvatar friend={selectedFriend} size={30} />}
                                <View className={`max-w-[78%] ${mine ? "items-end" : "items-start ml-2"}`}>
                                  <View
                                    className={`px-3.5 py-2.5 rounded-2xl ${mine ? "bg-cyan-700" : "bg-white border border-gray-200"}`}
                                  >
                                    <Text className={`text-sm leading-5 ${mine ? "text-white" : "text-gray-900"}`}>
                                      {message.content}
                                    </Text>
                                  </View>
                                  <Text className="text-[10px] text-gray-400 mt-1 px-1">
                                    {messageTime(message.created_at)}
                                  </Text>
                                </View>
                              </View>
                            );
                          })
                        )}
                      </ScrollView>
                    )}

                    <View className="px-4 py-3 border-t border-gray-100 bg-white">
                      <View className="min-h-12 rounded-2xl bg-gray-100 px-4 flex-row items-center">
                        <TextInput
                          value={draft}
                          onChangeText={setDraft}
                          editable={!!roomId && !roomQuery.isError}
                          placeholder="메시지를 입력하세요"
                          placeholderTextColor="#94A3B8"
                          className="flex-1 text-sm text-gray-900"
                          multiline
                          maxLength={10000}
                        />
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel="메시지 보내기"
                          onPress={sendMessage}
                          disabled={!roomId || !draft.trim() || sendMutation.isPending}
                          className={`w-9 h-9 rounded-xl items-center justify-center ${
                            roomId && draft.trim() && !sendMutation.isPending ? "bg-cyan-700" : "bg-gray-200"
                          }`}
                        >
                          {sendMutation.isPending ? (
                            <ActivityIndicator size="small" color="white" />
                          ) : (
                            <Send size={17} color={roomId && draft.trim() ? "white" : "#94A3B8"} />
                          )}
                        </Pressable>
                      </View>
                      {!!sendError && <Text className="mt-2 text-xs text-red-600">{sendError}</Text>}
                    </View>
                  </>
                ) : (
                  <View className="flex-1 items-center justify-center px-8 bg-[#FBFDFD]">
                    <View className="w-24 h-24 rounded-full bg-cyan-50 items-center justify-center">
                      <MessageCircle size={42} color={BRAND} />
                    </View>
                    <Text className="text-xl font-extrabold text-gray-800 mt-6">대화할 친구를 선택하세요</Text>
                    <Text className="text-sm leading-6 text-gray-400 text-center mt-2">
                      왼쪽 친구 목록에서 친구를 선택하면{"\n"}쪽지 화면이 열립니다.
                    </Text>
                  </View>
                )}
              </View>
            )}
          </View>
        </View>
      </View>

      <FriendInviteModal
        visible={inviteModalVisible}
        onClose={() => setInviteModalVisible(false)}
      />
      <FriendTimetableModal
        visible={!!timetableFriend}
        friendId={timetableFriend?.id ?? null}
        friendName={timetableFriend?.name}
        onClose={() => setTimetableFriend(null)}
      />
    </AppScreenLayout>
  );
};
