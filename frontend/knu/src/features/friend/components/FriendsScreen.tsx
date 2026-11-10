import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, View } from "react-native";
import { CalendarDays, ChevronRight, MessageCircle, UserPlus, Users } from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { getAxiosErrorMessage } from "@/api/errors";
import { deleteFriend, getFriendRequests, getFriends } from "@/features/friend/api/friend";
import type { FriendUser } from "@/features/friend/api/types";

import { FriendInviteModal } from "./FriendInviteModal";
import { FriendTimetableModal } from "./FriendTimetableModal";

const BRAND = "#13708D";

export const FriendsScreen = () => {
  const client = useQueryClient();
  const [inviteVisible, setInviteVisible] = useState(false);
  const [timetableFriend, setTimetableFriend] = useState<FriendUser | null>(null);

  const friendsQuery = useQuery({ queryKey: ["friends"], queryFn: getFriends });
  const requestsQuery = useQuery({ queryKey: ["friendRequests"], queryFn: getFriendRequests });
  const friends = friendsQuery.data ?? [];
  const pendingCount = requestsQuery.data?.received.length ?? 0;

  const deleteMutation = useMutation({
    mutationFn: deleteFriend,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["friends"] });
      void client.invalidateQueries({ queryKey: ["friendRequests"] });
      void client.invalidateQueries({ queryKey: ["chatRooms"] });
      void client.invalidateQueries({ queryKey: ["directChatRoom"] });
    },
    onError: (error) => Alert.alert("삭제 실패", getAxiosErrorMessage(error, "친구 삭제에 실패했습니다.")),
  });

  const openFriendActions = (friend: FriendUser) => {
    Alert.alert(friend.name, "친구 관리 메뉴입니다.", [
      { text: "취소", style: "cancel" },
      { text: "친구 삭제", style: "destructive", onPress: () => deleteMutation.mutate(friend.id) },
    ]);
  };

  return (
    <AppScreenLayout>
      <View className="flex-1 bg-[#F4F7F8] p-3">
        <View className="flex-1 bg-white rounded-[28px] border border-gray-200 overflow-hidden">
          <View className="px-5 pt-6 pb-4 border-b border-gray-100 flex-row items-center">
            <View className="flex-1"><Text className="text-2xl font-extrabold text-gray-900">친구</Text><Text className="text-sm text-gray-400 mt-1">친구를 관리하고 시간표를 확인하세요.</Text></View>
            <Pressable onPress={() => setInviteVisible(true)} className="h-11 px-4 rounded-2xl flex-row items-center" style={{ backgroundColor: BRAND }}><UserPlus size={18} color="white" /><Text className="ml-2 text-sm font-extrabold text-white">친구 초대</Text></Pressable>
          </View>

          {pendingCount > 0 && <Pressable onPress={() => setInviteVisible(true)} className="mx-4 mt-4 p-4 rounded-2xl bg-amber-50 border border-amber-100 flex-row items-center"><View className="w-10 h-10 rounded-full bg-amber-100 items-center justify-center"><Users size={19} color="#B45309" /></View><View className="flex-1 ml-3"><Text className="text-sm font-extrabold text-amber-900">받은 친구 요청 {pendingCount}건</Text><Text className="text-xs text-amber-700 mt-1">누르면 요청을 확인할 수 있어요.</Text></View><ChevronRight size={18} color="#B45309" /></Pressable>}

          <View className="px-5 pt-5 pb-2 flex-row items-center justify-between"><Text className="text-xs font-extrabold text-gray-500 tracking-wider">친구 목록</Text><Text className="text-xs font-bold text-gray-400">{friends.length}명</Text></View>
          {friendsQuery.isLoading ? <View className="flex-1 items-center justify-center"><ActivityIndicator color={BRAND} /></View> : friendsQuery.isError ? <View className="flex-1 items-center justify-center px-8"><Text className="text-sm text-gray-500">친구 목록을 불러오지 못했습니다.</Text><Pressable onPress={() => friendsQuery.refetch()} className="mt-4 px-4 py-2 rounded-xl bg-cyan-50"><Text className="font-bold" style={{ color: BRAND }}>다시 시도</Text></Pressable></View> : friends.length === 0 ? <View className="flex-1 items-center justify-center px-8"><View className="w-16 h-16 rounded-full bg-cyan-50 items-center justify-center"><Users size={30} color={BRAND} /></View><Text className="text-base font-extrabold text-gray-800 mt-4">등록된 친구가 없어요.</Text><Text className="text-xs text-gray-400 text-center mt-2">친구 초대를 눌러 새 친구를 추가해보세요.</Text></View> : (
            <ScrollView contentContainerStyle={{ paddingHorizontal: 10, paddingBottom: 16 }} showsVerticalScrollIndicator={false}>
              {friends.map((friend) => <Pressable key={friend.id} onLongPress={() => openFriendActions(friend)} delayLongPress={500} className="p-4 rounded-2xl flex-row items-center active:bg-gray-50"><View className="w-12 h-12 rounded-full bg-cyan-50 border border-cyan-100 items-center justify-center"><Text className="font-extrabold text-lg" style={{ color: BRAND }}>{friend.name.slice(0, 1)}</Text></View><View className="flex-1 ml-3"><Text className="text-[15px] font-extrabold text-gray-900">{friend.name}</Text><Text className="text-xs text-gray-400 mt-1" numberOfLines={1}>{[friend.department, friend.student_id].filter(Boolean).join(" · ") || friend.email}</Text></View><View className="flex-row" style={{ gap: 6 }}><Pressable onPress={() => router.push({ pathname: "/(app)/(tabs)/messages", params: { friendId: String(friend.id) } })} className="h-10 px-3 rounded-xl bg-cyan-50 flex-row items-center"><MessageCircle size={16} color={BRAND} /><Text className="ml-1 text-xs font-extrabold text-cyan-800">채팅</Text></Pressable><Pressable onPress={() => setTimetableFriend(friend)} className="h-10 px-3 rounded-xl bg-gray-100 flex-row items-center"><CalendarDays size={16} color="#64748B" /><Text className="ml-1 text-xs font-extrabold text-gray-600">시간표</Text></Pressable></View></Pressable>)}
            </ScrollView>
          )}
        </View>
      </View>
      <FriendInviteModal visible={inviteVisible} onClose={() => setInviteVisible(false)} />
      <FriendTimetableModal visible={!!timetableFriend} friendId={timetableFriend?.id ?? null} friendName={timetableFriend?.name} onClose={() => setTimetableFriend(null)} />
    </AppScreenLayout>
  );
};
