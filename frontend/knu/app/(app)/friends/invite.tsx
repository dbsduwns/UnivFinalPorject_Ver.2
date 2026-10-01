import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { CheckCircle2, Link2, UserPlus, XCircle } from "lucide-react-native";

import { getAxiosErrorMessage } from "@/api/errors";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import {
  acceptFriendInviteLink,
  getFriendInvitePreview,
} from "@/features/friend/api/friend";
import { useAuthStore } from "@/features/auth/store/auth-store";

const BRAND = "#13708D";

export default function FriendInvitePage() {
  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const token = Array.isArray(params.token) ? params.token[0] : params.token;
  const ready = useAuthStore((state) => state.ready);
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!ready || user || !token) return;
    router.replace({
      pathname: "/(auth)/login",
      params: { redirect: `/(app)/friends/invite?token=${encodeURIComponent(token)}` },
    });
  }, [ready, token, user]);

  const previewQuery = useQuery({
    queryKey: ["friendInvite", token],
    queryFn: () => getFriendInvitePreview(token!),
    enabled: ready && !!user && !!token,
    retry: false,
  });

  const acceptMutation = useMutation({
    mutationFn: () => acceptFriendInviteLink(token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["friends"] });
      void queryClient.invalidateQueries({ queryKey: ["friendRequests"] });
      void previewQuery.refetch();
    },
  });

  if (!ready || !user) return null;

  const isFriend = previewQuery.data?.friendship_status === "FRIEND" || acceptMutation.isSuccess;

  return (
    <AppScreenLayout>
      <View className="flex-1 bg-[#F4F7F8] px-5 items-center justify-center">
        <View className="w-full max-w-md bg-white rounded-[30px] border border-gray-200 p-7 items-center shadow-sm">
          {!token || previewQuery.isError ? (
            <>
              <View className="w-20 h-20 rounded-full bg-rose-50 items-center justify-center">
                <XCircle size={38} color="#E11D48" />
              </View>
              <Text className="text-xl font-extrabold text-gray-900 mt-5">초대 링크를 열 수 없어요</Text>
              <Text className="text-sm leading-6 text-gray-400 text-center mt-2">
                {previewQuery.error
                  ? getAxiosErrorMessage(previewQuery.error, "유효하지 않거나 만료된 초대 링크입니다.")
                  : "초대 정보가 없는 링크입니다."}
              </Text>
            </>
          ) : previewQuery.isLoading ? (
            <>
              <ActivityIndicator size="large" color={BRAND} />
              <Text className="text-sm text-gray-400 mt-4">친구 초대를 확인하고 있어요.</Text>
            </>
          ) : isFriend ? (
            <>
              <View className="w-20 h-20 rounded-full bg-emerald-50 items-center justify-center">
                <CheckCircle2 size={40} color="#059669" />
              </View>
              <Text className="text-xl font-extrabold text-gray-900 mt-5">친구가 되었어요!</Text>
              <Text className="text-sm text-gray-400 text-center mt-2">
                {previewQuery.data?.inviter.name} 님과 이제 쪽지와 시간표를 공유할 수 있어요.
              </Text>
            </>
          ) : (
            <>
              <View className="w-20 h-20 rounded-full bg-cyan-50 items-center justify-center">
                <UserPlus size={36} color={BRAND} />
              </View>
              <Text className="text-xl font-extrabold text-gray-900 mt-5">친구 초대가 도착했어요</Text>
              <Text className="text-base font-bold text-gray-700 mt-3">
                {previewQuery.data?.inviter.name}
              </Text>
              <Text className="text-sm text-gray-400 mt-1">
                {previewQuery.data?.inviter.department || previewQuery.data?.inviter.email}
              </Text>
              {acceptMutation.isError && (
                <Text className="text-xs text-rose-600 text-center mt-4">
                  {getAxiosErrorMessage(acceptMutation.error, "초대를 수락하지 못했습니다.")}
                </Text>
              )}
              <Pressable
                disabled={acceptMutation.isPending}
                onPress={() => acceptMutation.mutate()}
                className="w-full h-13 mt-6 rounded-2xl flex-row items-center justify-center disabled:opacity-40"
                style={{ backgroundColor: BRAND }}
              >
                {acceptMutation.isPending ? (
                  <ActivityIndicator color="white" />
                ) : (
                  <>
                    <Link2 size={18} color="white" />
                    <Text className="text-white font-extrabold ml-2">친구 초대 수락하기</Text>
                  </>
                )}
              </Pressable>
            </>
          )}

          <Pressable onPress={() => router.replace("/(app)/messages")} className="mt-5 py-3 px-5">
            <Text className="text-sm font-bold" style={{ color: BRAND }}>쪽지 화면으로 이동</Text>
          </Pressable>
        </View>
      </View>
    </AppScreenLayout>
  );
}
