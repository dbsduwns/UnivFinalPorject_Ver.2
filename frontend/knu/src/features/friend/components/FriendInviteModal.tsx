import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Share,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  Check,
  Clock3,
  Link2,
  Mail,
  Send,
  Share2,
  UserCheck,
  UserPlus,
  X,
} from "lucide-react-native";

import { getAxiosErrorMessage } from "@/api/errors";
import { API_BASE_URL } from "@/constants/config";
import {
  acceptFriendRequest,
  cancelFriendRequest,
  createFriendInviteLink,
  getFriendRequests,
  rejectFriendRequest,
  searchFriends,
  sendFriendRequest,
} from "@/features/friend/api/friend";

type Props = {
  visible: boolean;
  onClose: () => void;
};

type Tab = "invite" | "requests";
type InviteMethod = "direct" | "link";

const BRAND = "#13708D";

export const FriendInviteModal = ({ visible, onClose }: Props) => {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("invite");
  const [method, setMethod] = useState<InviteMethod>("direct");
  const [identifier, setIdentifier] = useState("");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);

  const requestsQuery = useQuery({
    queryKey: ["friendRequests"],
    queryFn: getFriendRequests,
    enabled: visible,
  });

  const directInviteMutation = useMutation({
    mutationFn: async (value: string) => {
      const normalized = value.trim().toLocaleLowerCase();
      const results = await searchFriends(value.trim());
      const match = results.find(
        ({ user }) =>
          user.email.toLocaleLowerCase() === normalized ||
          user.student_id?.toLocaleLowerCase() === normalized
      );

      if (!match) {
        throw new Error("일치하는 아이디 또는 이메일 주소를 찾을 수 없습니다.");
      }
      if (match.friendship_status === "FRIEND") {
        throw new Error("이미 친구로 등록된 사용자입니다.");
      }
      if (match.friendship_status === "PENDING_SENT") {
        throw new Error("이미 친구 초대를 보낸 사용자입니다.");
      }

      return sendFriendRequest({ addressee_id: match.user.id });
    },
    onSuccess: () => {
      setIdentifier("");
      void queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      void queryClient.invalidateQueries({ queryKey: ["friends"] });
      Alert.alert("초대 완료", "친구 초대를 보냈습니다.");
    },
    onError: (error) => {
      const message = error instanceof Error && !isAxiosError(error)
        ? error.message
        : getAxiosErrorMessage(error, "친구 초대를 보내지 못했습니다.");
      Alert.alert("초대 실패", message);
    },
  });

  const linkMutation = useMutation({
    mutationFn: createFriendInviteLink,
    onSuccess: ({ token }) => {
      // 운영 서버 랜딩 페이지가 앱 딥링크로 전달하고,
      // 앱이 없으면 설치 안내를 보여줍니다.
      const url = `${API_BASE_URL}/api/friends/invite/${encodeURIComponent(token)}`;
      setInviteUrl(url);
    },
    onError: (error) => {
      Alert.alert("링크 생성 실패", getAxiosErrorMessage(error, "초대 링크를 만들지 못했습니다."));
    },
  });

  const acceptMutation = useMutation({
    mutationFn: acceptFriendRequest,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      void queryClient.invalidateQueries({ queryKey: ["friends"] });
    },
    onError: (error) => Alert.alert("수락 실패", getAxiosErrorMessage(error)),
  });

  const rejectMutation = useMutation({
    mutationFn: rejectFriendRequest,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["friendRequests"] }),
    onError: (error) => Alert.alert("거절 실패", getAxiosErrorMessage(error)),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelFriendRequest,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["friendRequests"] }),
    onError: (error) => Alert.alert("취소 실패", getAxiosErrorMessage(error)),
  });

  const received = requestsQuery.data?.received ?? [];
  const sent = requestsQuery.data?.sent ?? [];

  const shareInviteLink = async () => {
    if (!inviteUrl) return;
    try {
      await Share.share({
        title: "KNU Campus 친구 초대",
        message: `KNU Campus에서 친구 초대가 도착했어요. 아래 링크를 열어 초대를 수락해주세요.\n${inviteUrl}`,
        url: inviteUrl,
      });
    } catch {
      Alert.alert("공유 실패", "초대 링크를 공유하지 못했습니다.");
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 bg-black/45 justify-end sm:justify-center sm:items-center">
        <View className="w-full sm:w-[92%] max-w-xl h-[88%] bg-[#F7F9FA] rounded-t-[30px] sm:rounded-[30px] overflow-hidden">
          <View className="px-5 py-4 bg-white border-b border-gray-100 flex-row items-center">
            <View className="w-10 h-10 rounded-2xl bg-cyan-50 items-center justify-center">
              <UserPlus size={20} color={BRAND} />
            </View>
            <View className="flex-1 ml-3">
              <Text className="text-lg font-extrabold text-gray-900">친구 초대</Text>
              <Text className="text-xs text-gray-400 mt-0.5">친구를 초대하거나 받은 요청을 확인하세요.</Text>
            </View>
            <Pressable onPress={onClose} className="w-10 h-10 rounded-full bg-gray-100 items-center justify-center">
              <X size={20} color="#64748B" />
            </Pressable>
          </View>

          <View className="flex-row bg-white px-4 border-b border-gray-100">
            <Pressable
              onPress={() => setTab("invite")}
              className={`flex-1 py-4 border-b-2 items-center ${tab === "invite" ? "border-cyan-700" : "border-transparent"}`}
            >
              <Text className={`text-sm font-extrabold ${tab === "invite" ? "text-cyan-800" : "text-gray-400"}`}>
                친구 초대
              </Text>
            </Pressable>
            <Pressable
              onPress={() => setTab("requests")}
              className={`flex-1 py-4 border-b-2 items-center ${tab === "requests" ? "border-cyan-700" : "border-transparent"}`}
            >
              <View className="flex-row items-center">
                <Text className={`text-sm font-extrabold ${tab === "requests" ? "text-cyan-800" : "text-gray-400"}`}>
                  초대 요청 수락
                </Text>
                {received.length > 0 && (
                  <View className="ml-2 min-w-5 h-5 px-1 rounded-full bg-rose-500 items-center justify-center">
                    <Text className="text-[10px] text-white font-extrabold">{received.length}</Text>
                  </View>
                )}
              </View>
            </Pressable>
          </View>

          {tab === "invite" ? (
            <ScrollView className="flex-1" contentContainerStyle={{ padding: 16, paddingBottom: 30 }}>
              <Text className="text-xs font-extrabold text-gray-500 mb-3 ml-1">초대 방법을 선택하세요</Text>
              <View className="flex-row" style={{ gap: 10 }}>
                <MethodButton
                  active={method === "direct"}
                  icon={<Mail size={20} color={method === "direct" ? BRAND : "#64748B"} />}
                  title="아이디 · 이메일"
                  description="직접 찾아서 초대"
                  onPress={() => setMethod("direct")}
                />
                <MethodButton
                  active={method === "link"}
                  icon={<Link2 size={20} color={method === "link" ? BRAND : "#64748B"} />}
                  title="초대 링크"
                  description="링크로 간편 초대"
                  onPress={() => setMethod("link")}
                />
              </View>

              {method === "direct" ? (
                <View className="mt-5 bg-white rounded-3xl border border-gray-200 p-5">
                  <View className="w-12 h-12 rounded-2xl bg-cyan-50 items-center justify-center">
                    <Send size={22} color={BRAND} />
                  </View>
                  <Text className="text-lg font-extrabold text-gray-900 mt-4">아이디 또는 이메일로 초대</Text>
                  <Text className="text-sm leading-5 text-gray-400 mt-1.5">
                    정확한 학번 아이디 또는 학교 이메일 주소를 입력해주세요.
                  </Text>
                  <TextInput
                    value={identifier}
                    onChangeText={setIdentifier}
                    onSubmitEditing={() => {
                      if (identifier.trim()) directInviteMutation.mutate(identifier);
                    }}
                    placeholder="예: 202612345 또는 student@kangnam.ac.kr"
                    placeholderTextColor="#94A3B8"
                    autoCapitalize="none"
                    keyboardType="email-address"
                    returnKeyType="send"
                    className="h-13 mt-5 px-4 rounded-2xl bg-gray-100 text-sm text-gray-900"
                  />
                  <Pressable
                    disabled={!identifier.trim() || directInviteMutation.isPending}
                    onPress={() => directInviteMutation.mutate(identifier)}
                    className="h-12 mt-3 rounded-2xl items-center justify-center disabled:opacity-40"
                    style={{ backgroundColor: BRAND }}
                  >
                    {directInviteMutation.isPending ? (
                      <ActivityIndicator color="white" />
                    ) : (
                      <Text className="text-white font-extrabold">친구 초대 보내기</Text>
                    )}
                  </Pressable>
                </View>
              ) : (
                <View className="mt-5 bg-white rounded-3xl border border-gray-200 p-5">
                  <View className="w-12 h-12 rounded-2xl bg-cyan-50 items-center justify-center">
                    <Share2 size={22} color={BRAND} />
                  </View>
                  <Text className="text-lg font-extrabold text-gray-900 mt-4">초대 링크 공유</Text>
                  <Text className="text-sm leading-5 text-gray-400 mt-1.5">
                    링크는 7일 동안 유효하며, KNU Campus에 로그인한 친구가 사용할 수 있어요.
                  </Text>

                  {inviteUrl ? (
                    <>
                      <View className="mt-5 p-4 rounded-2xl bg-gray-100 flex-row items-center">
                        <Link2 size={18} color={BRAND} />
                        <Text className="flex-1 ml-2 text-xs text-gray-600" numberOfLines={2}>{inviteUrl}</Text>
                        <Check size={18} color="#059669" />
                      </View>
                      <Pressable
                        onPress={() => void shareInviteLink()}
                        className="h-12 mt-3 rounded-2xl flex-row items-center justify-center"
                        style={{ backgroundColor: BRAND }}
                      >
                        <Share2 size={18} color="white" />
                        <Text className="text-white font-extrabold ml-2">초대 링크 공유하기</Text>
                      </Pressable>
                      <Pressable onPress={() => linkMutation.mutate()} className="mt-4 items-center py-2">
                        <Text className="text-xs font-bold text-gray-400">새 링크 만들기</Text>
                      </Pressable>
                    </>
                  ) : (
                    <Pressable
                      disabled={linkMutation.isPending}
                      onPress={() => linkMutation.mutate()}
                      className="h-12 mt-5 rounded-2xl flex-row items-center justify-center disabled:opacity-40"
                      style={{ backgroundColor: BRAND }}
                    >
                      {linkMutation.isPending ? (
                        <ActivityIndicator color="white" />
                      ) : (
                        <>
                          <Link2 size={18} color="white" />
                          <Text className="text-white font-extrabold ml-2">초대 링크 만들기</Text>
                        </>
                      )}
                    </Pressable>
                  )}
                </View>
              )}
            </ScrollView>
          ) : (
            <ScrollView className="flex-1" contentContainerStyle={{ padding: 16, paddingBottom: 30 }}>
              <Text className="text-xs font-extrabold text-gray-500 mb-3 ml-1">받은 초대 ({received.length})</Text>
              {requestsQuery.isLoading ? (
                <ActivityIndicator color={BRAND} className="py-12" />
              ) : received.length === 0 ? (
                <View className="bg-white rounded-3xl border border-dashed border-gray-200 py-12 items-center">
                  <UserCheck size={38} color="#CBD5E1" />
                  <Text className="text-sm font-bold text-gray-500 mt-4">새로운 친구 초대가 없어요.</Text>
                </View>
              ) : (
                received.map((request) => (
                  <View key={request.id} className="bg-white rounded-2xl border border-gray-200 p-4 mb-2 flex-row items-center">
                    <View className="w-11 h-11 rounded-full bg-cyan-50 items-center justify-center">
                      <Text className="font-extrabold" style={{ color: BRAND }}>{request.user.name.slice(0, 1)}</Text>
                    </View>
                    <View className="flex-1 ml-3">
                      <Text className="text-sm font-extrabold text-gray-900">{request.user.name}</Text>
                      <Text className="text-xs text-gray-400 mt-1" numberOfLines={1}>
                        {request.user.department || request.user.student_id || request.user.email}
                      </Text>
                    </View>
                    <Pressable onPress={() => rejectMutation.mutate(request.id)} className="px-3 py-2 rounded-xl bg-gray-100">
                      <Text className="text-xs font-bold text-gray-500">거절</Text>
                    </Pressable>
                    <Pressable onPress={() => acceptMutation.mutate(request.id)} className="ml-2 px-3 py-2 rounded-xl" style={{ backgroundColor: BRAND }}>
                      <Text className="text-xs font-bold text-white">수락</Text>
                    </Pressable>
                  </View>
                ))
              )}

              <Text className="text-xs font-extrabold text-gray-500 mt-7 mb-3 ml-1">보낸 초대 ({sent.length})</Text>
              {sent.length === 0 ? (
                <View className="bg-white rounded-2xl border border-dashed border-gray-200 py-6 items-center">
                  <Text className="text-xs text-gray-400">기다리는 초대가 없습니다.</Text>
                </View>
              ) : (
                sent.map((request) => (
                  <View key={request.id} className="bg-white rounded-2xl border border-gray-200 p-4 mb-2 flex-row items-center">
                    <Clock3 size={19} color="#94A3B8" />
                    <View className="flex-1 ml-3">
                      <Text className="text-sm font-bold text-gray-800">{request.user.name}</Text>
                      <Text className="text-xs text-gray-400 mt-0.5">수락을 기다리고 있어요.</Text>
                    </View>
                    <Pressable onPress={() => cancelMutation.mutate(request.id)} className="px-3 py-2 rounded-xl bg-gray-100">
                      <Text className="text-xs font-bold text-gray-500">초대 취소</Text>
                    </Pressable>
                  </View>
                ))
              )}
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
};

const MethodButton = ({
  active,
  icon,
  title,
  description,
  onPress,
}: {
  active: boolean;
  icon: React.ReactNode;
  title: string;
  description: string;
  onPress: () => void;
}) => (
  <Pressable
    onPress={onPress}
    className={`flex-1 p-4 rounded-2xl border ${active ? "bg-cyan-50 border-cyan-600" : "bg-white border-gray-200"}`}
  >
    {icon}
    <Text className={`text-sm font-extrabold mt-3 ${active ? "text-cyan-900" : "text-gray-700"}`}>{title}</Text>
    <Text className="text-[11px] text-gray-400 mt-1">{description}</Text>
  </Pressable>
);
