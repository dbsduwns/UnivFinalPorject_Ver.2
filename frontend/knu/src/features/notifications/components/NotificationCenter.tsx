import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Modal,
  Pressable,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  BusFront,
  CheckCheck,
  MessageCircle,
  Megaphone,
  Utensils,
  X,
} from "lucide-react-native";

import { useAuthStore } from "@/features/auth/store/auth-store";
import { notificationApi } from "@/features/notifications/api/notifications";
import type { AppNotification } from "@/features/notifications/types";


const BRAND = "#13708D";

function notificationLabel(type: string) {
  if (type === "direct_message") return "채팅";
  if (type === "notice") return "공지사항";
  if (type === "cafeteria") return "학식";
  if (type === "shuttle") return "셔틀";
  return "알림";
}

function NotificationTypeIcon({ type }: { type: string }) {
  const iconProps = { size: 20, color: BRAND };
  if (type === "direct_message") return <MessageCircle {...iconProps} />;
  if (type === "notice") return <Megaphone {...iconProps} />;
  if (type === "cafeteria") return <Utensils {...iconProps} />;
  if (type === "shuttle") return <BusFront {...iconProps} />;
  return <Bell {...iconProps} />;
}

function formatNotificationTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return new Intl.DateTimeFormat("ko-KR", sameDay
    ? { hour: "2-digit", minute: "2-digit" }
    : { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
  ).format(date);
}

function dataValue(data: Record<string, unknown>, key: string) {
  const value = data[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function navigateFromNotification(notification: AppNotification) {
  const { notification_type: type, data } = notification;
  if (type === "direct_message") {
    const roomId = dataValue(data, "room_id");
    router.push({
      pathname: "/(app)/(tabs)/messages",
      params: roomId ? { roomId } : undefined,
    });
    return;
  }
  if (type === "notice") {
    const noticeId = dataValue(data, "notice_id");
    if (noticeId) {
      router.push({ pathname: "/(app)/notice/[id]", params: { id: noticeId } });
    } else {
      router.push("/(app)/(tabs)/notice");
    }
    return;
  }
  if (type === "cafeteria") {
    const date = dataValue(data, "menu_date");
    router.push({ pathname: "/(app)/(tabs)/meal", params: date ? { date } : undefined });
    return;
  }
  if (type === "shuttle") {
    const semester = dataValue(data, "semester");
    router.push({ pathname: "/(app)/(tabs)/shuttle", params: semester ? { semester } : undefined });
  }
}

function NotificationPanel({
  visible,
  onClose,
  items,
  unreadCount,
  isLoading,
  isError,
  isRefetching,
  onRefresh,
  onRead,
  onReadAll,
  isReadingAll,
}: {
  visible: boolean;
  onClose: () => void;
  items: AppNotification[];
  unreadCount: number;
  isLoading: boolean;
  isError: boolean;
  isRefetching: boolean;
  onRefresh: () => void;
  onRead: (notification: AppNotification) => void;
  onReadAll: () => void;
  isReadingAll: boolean;
}) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const panelWidth = Math.min(width * 0.9, 420);
  const [mounted, setMounted] = useState(visible);
  const translateX = useRef(new Animated.Value(panelWidth)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible && !mounted) {
      setMounted(true);
      return;
    }
    if (visible) {
      translateX.setValue(panelWidth);
      backdropOpacity.setValue(0);
      Animated.parallel([
        Animated.timing(translateX, {
          toValue: 0,
          duration: 260,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 1,
          duration: 220,
          useNativeDriver: true,
        }),
      ]).start();
      return;
    }
    if (mounted) {
      Animated.parallel([
        Animated.timing(translateX, {
          toValue: panelWidth,
          duration: 220,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 0,
          duration: 180,
          useNativeDriver: true,
        }),
      ]).start(({ finished }) => {
        if (finished) setMounted(false);
      });
    }
  }, [backdropOpacity, mounted, panelWidth, translateX, visible]);

  if (!mounted) return null;

  return (
    <Modal
      transparent
      visible={mounted}
      animationType="none"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View className="flex-1 flex-row justify-end">
        <Animated.View
          className="absolute inset-0 bg-black/40"
          style={{ opacity: backdropOpacity }}
        >
          <Pressable className="flex-1" onPress={onClose} accessibilityLabel="알림센터 닫기" />
        </Animated.View>
        <Animated.View
          className="h-full bg-[#F8FAFC] border-l border-gray-200"
          style={{
            width: panelWidth,
            paddingTop: insets.top,
            paddingBottom: insets.bottom,
            transform: [{ translateX }],
            elevation: 30,
          }}
        >
          <View className="h-16 px-5 flex-row items-center bg-white border-b border-gray-100">
            <View className="flex-1">
              <Text className="text-xl font-extrabold text-gray-900">알림센터</Text>
              <Text className="text-xs text-gray-500 mt-0.5">읽지 않은 알림 {unreadCount}개</Text>
            </View>
            {unreadCount > 0 && (
              <Pressable
                onPress={onReadAll}
                disabled={isReadingAll}
                accessibilityRole="button"
                accessibilityLabel="모든 알림 읽음 처리"
                className="h-10 px-3 mr-1 rounded-xl bg-cyan-50 flex-row items-center justify-center disabled:opacity-50"
              >
                <CheckCheck size={17} color={BRAND} />
                <Text className="ml-1 text-xs font-bold text-cyan-800">모두 읽음</Text>
              </Pressable>
            )}
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="알림센터 닫기"
              className="w-10 h-10 items-center justify-center rounded-xl"
            >
              <X size={23} color="#475569" />
            </Pressable>
          </View>

          <FlatList
            data={items}
            keyExtractor={(item) => String(item.id)}
            refreshing={isRefetching}
            onRefresh={onRefresh}
            contentContainerStyle={{ flexGrow: 1, paddingBottom: 24 }}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => onRead(item)}
                className={`mx-3 mt-3 p-4 rounded-2xl border ${item.read_at ? "bg-white border-gray-100" : "bg-cyan-50 border-cyan-100"}`}
              >
                <View className="flex-row items-start">
                  <View className="w-10 h-10 rounded-full bg-white items-center justify-center border border-gray-100">
                    <NotificationTypeIcon type={item.notification_type} />
                  </View>
                  <View className="flex-1 ml-3">
                    <View className="flex-row items-center">
                      <Text className="text-[11px] font-extrabold text-[#13708D]">
                        {notificationLabel(item.notification_type)}
                      </Text>
                      <Text className="ml-auto text-[11px] text-gray-400">
                        {formatNotificationTime(item.created_at)}
                      </Text>
                    </View>
                    <Text className="mt-1 text-[15px] font-extrabold text-gray-900" numberOfLines={2}>
                      {item.title}
                    </Text>
                    {!!item.body && item.body !== item.title && (
                      <Text className="mt-1 text-sm leading-5 text-gray-600" numberOfLines={3}>
                        {item.body}
                      </Text>
                    )}
                  </View>
                  {!item.read_at && <View className="w-2 h-2 rounded-full bg-orange-500 ml-2 mt-1" />}
                </View>
              </Pressable>
            )}
            ListEmptyComponent={(
              <View className="flex-1 items-center justify-center px-8">
                {isLoading ? (
                  <ActivityIndicator color={BRAND} />
                ) : isError ? (
                  <>
                    <Text className="text-sm text-gray-500">알림을 불러오지 못했습니다.</Text>
                    <Pressable onPress={onRefresh} className="mt-3 px-4 py-2 rounded-xl bg-cyan-50">
                      <Text className="font-bold text-cyan-800">다시 시도</Text>
                    </Pressable>
                  </>
                ) : (
                  <>
                    <Bell size={36} color="#CBD5E1" />
                    <Text className="mt-3 font-bold text-gray-500">아직 도착한 알림이 없습니다.</Text>
                    <Text className="mt-1 text-xs text-gray-400 text-center">채팅과 캠퍼스 업데이트 알림이 여기에 표시됩니다.</Text>
                  </>
                )}
              </View>
            )}
          />
        </Animated.View>
      </View>
    </Modal>
  );
}

export function NotificationCenterButton() {
  const [visible, setVisible] = useState(false);
  const userId = useAuthStore((state) => state.user?.id);
  const queryClient = useQueryClient();
  const queryKey = ["notifications", userId] as const;
  const notificationsQuery = useQuery({
    queryKey,
    queryFn: notificationApi.getNotifications,
    enabled: !!userId,
    refetchInterval: 15_000,
  });

  const markRead = useMutation({
    mutationFn: notificationApi.markRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAllRead = useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const unreadCount = notificationsQuery.data?.unread_count ?? 0;

  const handleNotificationPress = async (notification: AppNotification) => {
    if (!notification.read_at) {
      try {
        await markRead.mutateAsync(notification.id);
      } catch {
        // 알림 대상 화면으로 이동하는 동작은 읽음 API 실패와 무관하게 유지한다.
      }
    }
    setVisible(false);
    navigateFromNotification(notification);
  };

  return (
    <>
      <Pressable
        onPress={() => {
          setVisible(true);
          void notificationsQuery.refetch();
        }}
        accessibilityRole="button"
        accessibilityLabel={unreadCount > 0 ? `알림센터 열기, 읽지 않은 알림 ${unreadCount}개` : "알림센터 열기"}
        className="w-11 h-11 items-center justify-center rounded-full"
      >
        <Bell size={30} color="#6B7280" />
        {unreadCount > 0 && (
          <View className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-orange-500 border-2 border-white items-center justify-center">
            <Text className="text-[9px] leading-3 font-extrabold text-white">
              {unreadCount > 99 ? "99+" : unreadCount}
            </Text>
          </View>
        )}
      </Pressable>
      <NotificationPanel
        visible={visible}
        onClose={() => setVisible(false)}
        items={notificationsQuery.data?.items ?? []}
        unreadCount={unreadCount}
        isLoading={notificationsQuery.isLoading}
        isError={notificationsQuery.isError}
        isRefetching={notificationsQuery.isRefetching}
        onRefresh={() => { void notificationsQuery.refetch(); }}
        onRead={(notification) => { void handleNotificationPress(notification); }}
        onReadAll={() => markAllRead.mutate()}
        isReadingAll={markAllRead.isPending}
      />
    </>
  );
}
