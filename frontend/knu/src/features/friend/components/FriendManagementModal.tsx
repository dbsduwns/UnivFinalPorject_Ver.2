import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  X,
  Users,
  UserPlus,
  Inbox,
  Search,
  Calendar,
  Check,
  UserMinus,
  Clock,
  Send,
} from "lucide-react-native";

import {
  getFriends,
  getFriendRequests,
  searchFriends,
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  cancelFriendRequest,
  deleteFriend,
} from "../api/friend";
import type { FriendUser } from "../api/types";
import { FriendTimetableModal } from "./FriendTimetableModal";

type Props = {
  visible: boolean;
  onClose: () => void;
};

type TabType = "friends" | "requests" | "search";

export const FriendManagementModal = ({ visible, onClose }: Props) => {
  const [activeTab, setActiveTab] = useState<TabType>("friends");
  const [searchQuery, setSearchQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");

  // 친구 시간표 모달 상태
  const [timetableFriend, setTimetableFriend] = useState<{ id: number; name: string } | null>(null);

  const queryClient = useQueryClient();

  // 1. 친구 목록 쿼리
  const { data: friends = [], isLoading: isLoadingFriends } = useQuery({
    queryKey: ["friends"],
    queryFn: getFriends,
    enabled: visible,
  });

  // 2. 친구 요청 쿼리
  const { data: requests, isLoading: isLoadingRequests } = useQuery({
    queryKey: ["friendRequests"],
    queryFn: getFriendRequests,
    enabled: visible,
  });

  // 3. 친구 검색 쿼리
  const { data: searchResults = [], isLoading: isSearching } = useQuery({
    queryKey: ["searchFriends", submittedQuery],
    queryFn: () => (submittedQuery ? searchFriends(submittedQuery) : Promise.resolve([])),
    enabled: visible && !!submittedQuery,
  });

  // Mutation: 친구 요청 전송
  const sendRequestMutation = useMutation({
    mutationFn: (userId: number) => sendFriendRequest({ addressee_id: userId }),
    onSuccess: () => {
      Alert.alert("성공", "친구 요청을 보냈습니다.");
      queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      queryClient.invalidateQueries({ queryKey: ["searchFriends"] });
    },
    onError: (err: any) => {
      Alert.alert("오류", err?.response?.data?.detail || "친구 요청 전송에 실패했습니다.");
    },
  });

  // Mutation: 요청 수락
  const acceptMutation = useMutation({
    mutationFn: acceptFriendRequest,
    onSuccess: () => {
      Alert.alert("성공", "친구 요청을 수락했습니다.");
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      queryClient.invalidateQueries({ queryKey: ["searchFriends"] });
    },
    onError: (err: any) => {
      Alert.alert("오류", err?.response?.data?.detail || "수락 처리 중 오류가 발생했습니다.");
    },
  });

  // Mutation: 요청 거절
  const rejectMutation = useMutation({
    mutationFn: rejectFriendRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
    },
    onError: (err: any) => {
      Alert.alert("오류", err?.response?.data?.detail || "거절 처리 중 오류가 발생했습니다.");
    },
  });

  // Mutation: 보낸 요청 취소
  const cancelMutation = useMutation({
    mutationFn: cancelFriendRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      queryClient.invalidateQueries({ queryKey: ["searchFriends"] });
    },
    onError: (err: any) => {
      Alert.alert("오류", err?.response?.data?.detail || "요청 취소 중 오류가 발생했습니다.");
    },
  });

  // Mutation: 친구 삭제
  const deleteFriendMutation = useMutation({
    mutationFn: deleteFriend,
    onSuccess: () => {
      Alert.alert("완료", "친구 관계가 해제되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      queryClient.invalidateQueries({ queryKey: ["searchFriends"] });
    },
    onError: (err: any) => {
      Alert.alert("오류", err?.response?.data?.detail || "친구 삭제 중 오류가 발생했습니다.");
    },
  });

  const handleDeleteFriend = (friend: FriendUser) => {
    Alert.alert(
      "친구 삭제",
      `정말 ${friend.name} 님을 친구 목록에서 삭제하시겠습니까?`,
      [
        { text: "취소", style: "cancel" },
        {
          text: "삭제",
          style: "destructive",
          onPress: () => deleteFriendMutation.mutate(friend.id),
        },
      ]
    );
  };

  const handleSearchSubmit = () => {
    if (!searchQuery.trim()) return;
    setSubmittedQuery(searchQuery.trim());
  };

  const totalReceivedRequests = requests?.received?.length ?? 0;

  return (
    <>
      <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
        <View className="flex-1 bg-black/50 justify-end sm:justify-center items-center">
          <View className="bg-[#F8FAFC] w-full sm:w-[92%] max-w-xl h-[88%] rounded-t-3xl sm:rounded-3xl overflow-hidden flex-col shadow-2xl">
            {/* Header */}
            <View className="bg-white px-5 py-4 border-b border-gray-200 flex-row items-center justify-between">
              <View className="flex-row items-center space-x-2">
                <Users size={22} color="#0284C7" />
                <Text className="text-lg font-bold text-gray-900">친구 및 시간표 공유</Text>
              </View>
              <Pressable
                onPress={onClose}
                className="p-2 rounded-full bg-gray-100 active:bg-gray-200"
              >
                <X size={20} color="#475569" />
              </Pressable>
            </View>

            {/* Tabs */}
            <View className="flex-row bg-white border-b border-gray-200 px-3 pt-1">
              <Pressable
                onPress={() => setActiveTab("friends")}
                className={`flex-1 py-3 items-center border-b-2 ${
                  activeTab === "friends" ? "border-sky-600" : "border-transparent"
                }`}
              >
                <View className="flex-row items-center space-x-1.5">
                  <Users
                    size={16}
                    color={activeTab === "friends" ? "#0284C7" : "#64748B"}
                  />
                  <Text
                    className={`text-sm font-bold ${
                      activeTab === "friends" ? "text-sky-600" : "text-gray-500"
                    }`}
                  >
                    내 친구 ({friends.length})
                  </Text>
                </View>
              </Pressable>

              <Pressable
                onPress={() => setActiveTab("requests")}
                className={`flex-1 py-3 items-center border-b-2 relative ${
                  activeTab === "requests" ? "border-sky-600" : "border-transparent"
                }`}
              >
                <View className="flex-row items-center space-x-1.5">
                  <Inbox
                    size={16}
                    color={activeTab === "requests" ? "#0284C7" : "#64748B"}
                  />
                  <Text
                    className={`text-sm font-bold ${
                      activeTab === "requests" ? "text-sky-600" : "text-gray-500"
                    }`}
                  >
                    친구 요청
                  </Text>
                  {totalReceivedRequests > 0 && (
                    <View className="bg-rose-500 rounded-full px-1.5 py-0.2 items-center justify-center ml-1">
                      <Text className="text-[10px] text-white font-extrabold">
                        {totalReceivedRequests}
                      </Text>
                    </View>
                  )}
                </View>
              </Pressable>

              <Pressable
                onPress={() => setActiveTab("search")}
                className={`flex-1 py-3 items-center border-b-2 ${
                  activeTab === "search" ? "border-sky-600" : "border-transparent"
                }`}
              >
                <View className="flex-row items-center space-x-1.5">
                  <Search
                    size={16}
                    color={activeTab === "search" ? "#0284C7" : "#64748B"}
                  />
                  <Text
                    className={`text-sm font-bold ${
                      activeTab === "search" ? "text-sky-600" : "text-gray-500"
                    }`}
                  >
                    친구 찾기
                  </Text>
                </View>
              </Pressable>
            </View>

            {/* Content Area */}
            <View className="flex-1 p-4">
              {/* 1. 내 친구 목록 탭 */}
              {activeTab === "friends" && (
                <View className="flex-1">
                  {isLoadingFriends ? (
                    <View className="flex-1 items-center justify-center">
                      <ActivityIndicator size="large" color="#0284C7" />
                    </View>
                  ) : friends.length === 0 ? (
                    <View className="flex-1 items-center justify-center py-10">
                      <Users size={48} color="#CBD5E1" />
                      <Text className="text-base font-semibold text-gray-600 mt-4">
                        등록된 친구가 없습니다.
                      </Text>
                      <Text className="text-xs text-gray-400 mt-1 text-center">
                        '친구 찾기' 탭에서 학번이나 이름으로 친구를 검색하여 추가해보세요!
                      </Text>
                      <Pressable
                        onPress={() => setActiveTab("search")}
                        className="mt-5 px-5 py-2.5 bg-sky-600 rounded-xl active:bg-sky-700"
                      >
                        <Text className="text-xs font-bold text-white">친구 찾으러 가기</Text>
                      </Pressable>
                    </View>
                  ) : (
                    <ScrollView showsVerticalScrollIndicator={false}>
                      <View className="space-y-2.5">
                        {friends.map((item) => (
                          <View
                            key={item.id}
                            className="bg-white p-4 rounded-2xl border border-gray-200 flex-row items-center justify-between shadow-sm"
                          >
                            <View className="flex-row items-center space-x-3 flex-1 mr-3">
                              <View className="w-11 h-11 rounded-full bg-sky-100 items-center justify-center border border-sky-200">
                                <Text className="text-sky-700 font-bold text-base">
                                  {item.name.slice(0, 1)}
                                </Text>
                              </View>
                              <View className="flex-1">
                                <Text className="text-sm font-bold text-gray-900" numberOfLines={1}>
                                  {item.name}
                                </Text>
                                <Text className="text-xs text-gray-500 mt-0.5" numberOfLines={1}>
                                  {item.department ? `${item.department} ` : ""}
                                  {item.student_id ? `(${item.student_id})` : ""}
                                </Text>
                              </View>
                            </View>

                            <View className="flex-row items-center space-x-2">
                              {/* 시간표 보기 버튼 */}
                              <Pressable
                                onPress={() =>
                                  setTimetableFriend({ id: item.id, name: item.name })
                                }
                                className="px-3 py-2 bg-sky-600 rounded-xl flex-row items-center space-x-1.5 active:bg-sky-700 shadow-sm"
                              >
                                <Calendar size={14} color="white" />
                                <Text className="text-xs font-bold text-white">시간표</Text>
                              </Pressable>

                              {/* 친구 삭제 버튼 */}
                              <Pressable
                                onPress={() => handleDeleteFriend(item)}
                                className="p-2 bg-gray-100 rounded-xl active:bg-gray-200"
                              >
                                <UserMinus size={15} color="#94A3B8" />
                              </Pressable>
                            </View>
                          </View>
                        ))}
                      </View>
                    </ScrollView>
                  )}
                </View>
              )}

              {/* 2. 친구 요청 탭 */}
              {activeTab === "requests" && (
                <ScrollView showsVerticalScrollIndicator={false} className="flex-1">
                  {/* 받은 친구 요청 */}
                  <View className="mb-6">
                    <Text className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5 px-1">
                      받은 친구 요청 ({requests?.received?.length ?? 0})
                    </Text>

                    {isLoadingRequests ? (
                      <ActivityIndicator size="small" color="#0284C7" className="py-4" />
                    ) : (requests?.received?.length ?? 0) === 0 ? (
                      <View className="bg-white p-5 rounded-2xl border border-dashed border-gray-200 items-center">
                        <Text className="text-xs text-gray-400">받은 친구 요청이 없습니다.</Text>
                      </View>
                    ) : (
                      <View className="space-y-2">
                        {requests?.received.map((req) => (
                          <View
                            key={req.id}
                            className="bg-white p-3.5 rounded-2xl border border-gray-200 flex-row items-center justify-between"
                          >
                            <View className="flex-1 mr-3">
                              <Text className="text-sm font-bold text-gray-900">
                                {req.user.name}
                              </Text>
                              <Text className="text-xs text-gray-500">
                                {req.user.department || req.user.student_id || req.user.email}
                              </Text>
                            </View>
                            <View className="flex-row items-center space-x-2">
                              <Pressable
                                onPress={() => acceptMutation.mutate(req.id)}
                                className="px-3 py-1.5 bg-sky-600 rounded-xl active:bg-sky-700"
                              >
                                <Text className="text-xs font-bold text-white">수락</Text>
                              </Pressable>
                              <Pressable
                                onPress={() => rejectMutation.mutate(req.id)}
                                className="px-3 py-1.5 bg-gray-100 rounded-xl active:bg-gray-200"
                              >
                                <Text className="text-xs font-bold text-gray-600">거절</Text>
                              </Pressable>
                            </View>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>

                  {/* 보낸 친구 요청 */}
                  <View>
                    <Text className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5 px-1">
                      보낸 친구 요청 ({requests?.sent?.length ?? 0})
                    </Text>

                    {(requests?.sent?.length ?? 0) === 0 ? (
                      <View className="bg-white p-5 rounded-2xl border border-dashed border-gray-200 items-center">
                        <Text className="text-xs text-gray-400">보낸 친구 요청이 없습니다.</Text>
                      </View>
                    ) : (
                      <View className="space-y-2">
                        {requests?.sent.map((req) => (
                          <View
                            key={req.id}
                            className="bg-white p-3.5 rounded-2xl border border-gray-200 flex-row items-center justify-between"
                          >
                            <View className="flex-1 mr-3">
                              <Text className="text-sm font-bold text-gray-900">
                                {req.user.name}
                              </Text>
                              <Text className="text-xs text-gray-500">
                                {req.user.department || req.user.student_id || req.user.email}
                              </Text>
                            </View>
                            <Pressable
                              onPress={() => cancelMutation.mutate(req.id)}
                              className="px-3 py-1.5 bg-gray-100 rounded-xl active:bg-gray-200"
                            >
                              <Text className="text-xs font-semibold text-gray-500">요청 취소</Text>
                            </Pressable>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>
                </ScrollView>
              )}

              {/* 3. 친구 찾기 탭 */}
              {activeTab === "search" && (
                <View className="flex-1">
                  {/* Search Input */}
                  <View className="flex-row items-center bg-white border border-gray-300 rounded-2xl px-3.5 py-2.5 mb-4 shadow-sm">
                    <Search size={18} color="#94A3B8" />
                    <TextInput
                      className="flex-1 ml-2.5 text-sm text-gray-900"
                      placeholder="학번, 이름, 이메일로 검색"
                      placeholderTextColor="#94A3B8"
                      value={searchQuery}
                      onChangeText={setSearchQuery}
                      onSubmitEditing={handleSearchSubmit}
                      returnKeyType="search"
                      autoCapitalize="none"
                    />
                    {searchQuery.length > 0 && (
                      <Pressable onPress={() => setSearchQuery("")} className="p-1">
                        <X size={16} color="#94A3B8" />
                      </Pressable>
                    )}
                  </View>

                  {/* Search Results */}
                  <View className="flex-1">
                    {isSearching ? (
                      <View className="flex-1 items-center justify-center">
                        <ActivityIndicator size="large" color="#0284C7" />
                        <Text className="mt-3 text-xs text-gray-500">검색 중입니다...</Text>
                      </View>
                    ) : !submittedQuery ? (
                      <View className="flex-1 items-center justify-center py-10">
                        <Search size={44} color="#CBD5E1" />
                        <Text className="text-sm font-semibold text-gray-500 mt-3">
                          친구를 검색해보세요
                        </Text>
                        <Text className="text-xs text-gray-400 mt-1">
                          강남대학교 학우의 학번 또는 이름을 입력하세요.
                        </Text>
                      </View>
                    ) : searchResults.length === 0 ? (
                      <View className="flex-1 items-center justify-center py-10">
                        <Text className="text-sm font-semibold text-gray-500">
                          검색 결과가 없습니다.
                        </Text>
                        <Text className="text-xs text-gray-400 mt-1">
                          정확한 학번이나 이름을 확인해주세요.
                        </Text>
                      </View>
                    ) : (
                      <ScrollView showsVerticalScrollIndicator={false}>
                        <View className="space-y-2.5">
                          {searchResults.map((item) => (
                            <View
                              key={item.user.id}
                              className="bg-white p-4 rounded-2xl border border-gray-200 flex-row items-center justify-between"
                            >
                              <View className="flex-1 mr-3">
                                <Text className="text-sm font-bold text-gray-900">
                                  {item.user.name}
                                </Text>
                                <Text className="text-xs text-gray-500 mt-0.5">
                                  {item.user.department ? `${item.user.department} · ` : ""}
                                  {item.user.student_id ? `${item.user.student_id}` : item.user.email}
                                </Text>
                              </View>

                              {/* State Buttons */}
                              {item.friendship_status === "FRIEND" ? (
                                <View className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-xl flex-row items-center space-x-1">
                                  <Check size={13} color="#059669" />
                                  <Text className="text-xs font-bold text-emerald-700">친구</Text>
                                </View>
                              ) : item.friendship_status === "PENDING_SENT" ? (
                                <View className="px-3 py-1.5 bg-gray-100 rounded-xl flex-row items-center space-x-1">
                                  <Clock size={13} color="#64748B" />
                                  <Text className="text-xs font-medium text-gray-600">
                                    요청 보냄
                                  </Text>
                                </View>
                              ) : item.friendship_status === "PENDING_RECEIVED" ? (
                                <Pressable
                                  onPress={() =>
                                    item.request_id && acceptMutation.mutate(item.request_id)
                                  }
                                  className="px-3 py-1.5 bg-sky-600 rounded-xl active:bg-sky-700"
                                >
                                  <Text className="text-xs font-bold text-white">수락하기</Text>
                                </Pressable>
                              ) : (
                                <Pressable
                                  onPress={() => sendRequestMutation.mutate(item.user.id)}
                                  className="px-3.5 py-1.5 bg-sky-600 rounded-xl flex-row items-center space-x-1 active:bg-sky-700"
                                >
                                  <UserPlus size={14} color="white" />
                                  <Text className="text-xs font-bold text-white">친구 신청</Text>
                                </Pressable>
                              )}
                            </View>
                          ))}
                        </View>
                      </ScrollView>
                    )}
                  </View>
                </View>
              )}
            </View>
          </View>
        </View>
      </Modal>

      {/* 친구 시간표 뷰어 모달 */}
      <FriendTimetableModal
        visible={!!timetableFriend}
        friendId={timetableFriend?.id ?? null}
        friendName={timetableFriend?.name}
        onClose={() => setTimetableFriend(null)}
      />
    </>
  );
};
