import "react-native-gesture-handler";
import "../global.css";

import { useEffect, useRef } from "react";
import { DarkTheme, DefaultTheme, ThemeProvider } from "@react-navigation/native";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";
import { AppState, type AppStateStatus } from "react-native";
import "react-native-reanimated";

import { QueryProvider } from "@/components/providers/query-provider";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { presenceApi } from "@/features/presence/api/presence-api";
import { usePresenceStore } from "@/features/presence/store/presence-store";
import { useAuthBootstrap } from "@/hooks/use-auth-bootstrap";
import { useColorScheme } from "@/hooks/use-color-scheme";

// 앱 최상단에서 포그라운드 알림 핸들러 등록
Notifications.setNotificationHandler({
  handleNotification: async (notification) => {
    const data = notification.request.content.data;
    const roomId = Number(data.room_id);
    const currentUserId = useAuthStore.getState().user?.id;
    const isViewingMessageRoom =
      data.type === "direct_message"
      && data.recipient_id === currentUserId
      && AppState.currentState === "active"
      && Number.isInteger(roomId)
      && usePresenceStore.getState().activeRoomId === roomId;

    if (isViewingMessageRoom) {
      return {
        shouldShowAlert: false,
        shouldShowBanner: false,
        shouldShowList: false,
        shouldPlaySound: false,
        shouldSetBadge: false,
      };
    }

    return {
      shouldShowAlert: true,
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    };
  },
});

function handleNotificationResponse(response: Notifications.NotificationResponse) {
  const data = response.notification.request.content.data;

  if (data.type === "direct_message") {
    router.push({
      pathname: "/(app)/(tabs)/messages",
      params: { roomId: String(data.room_id) },
    });
  }

  if (data.type === "notice") {
    router.push({
      pathname: "/(app)/notice/[id]",
      params: { id: String(data.notice_id) },
    });
  }

  if (data.type === "cafeteria") {
    const menuDate = typeof data.menu_date === "string" ? data.menu_date : "";
    router.push({
      pathname: "/(app)/(tabs)/meal",
      params: menuDate ? { date: menuDate } : undefined,
    });
  }

  if (data.type === "shuttle") {
    const semester = typeof data.semester === "string" ? data.semester : "";
    router.push({
      pathname: "/(app)/(tabs)/shuttle",
      params: semester ? { semester } : undefined,
    });
  }
};

export const unstable_settings = {
  initialRouteName: "(app)/(tabs)",
};

function NavigationTree() {
  const userId = useAuthStore((state) => state.user?.id);
  const appState = useRef<AppStateStatus>(AppState.currentState);

  useEffect(() => {
    // 앱 실행 중 또는 백그라운드에서 알림을 누른 경우
    const subscription = Notifications.addNotificationResponseReceivedListener(handleNotificationResponse);
    // 앱이 완전히 종료된 상태에서 알림을 눌러 시작된 경우
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) {
        handleNotificationResponse(response);
      }
    });

    return () => subscription.remove();
  }, []);

  useAuthBootstrap();
  const colorScheme = useColorScheme();

  useEffect(() => {
    if (!userId) return;

    const syncPresence = (isAppForeground: boolean) => {
      const activeRoomId = isAppForeground
        ? usePresenceStore.getState().activeRoomId
        : null;
      void presenceApi.updateMyPresence({
        active_room_id: activeRoomId,
        is_app_foreground: isAppForeground,
      }).catch(() => undefined);
    };

    syncPresence(appState.current === "active");

    const subscription = AppState.addEventListener("change", (nextState) => {
      appState.current = nextState;
      syncPresence(nextState === "active");
    });
    const heartbeat = setInterval(() => {
      if (appState.current === "active") syncPresence(true);
    }, 45_000);

    return () => {
      subscription.remove();
      clearInterval(heartbeat);
    };
  }, [userId]);

  return (
    <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(app)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: "modal", title: "Modal" }} />
      </Stack>
      <StatusBar
        style="dark"
        hidden={false}
        backgroundColor="#FFFFFF"
        translucent={false}
      />
    </ThemeProvider>
  );
}

export default function RootLayout() {
  return (
    <QueryProvider>
      <NavigationTree />
    </QueryProvider>
  );
}
