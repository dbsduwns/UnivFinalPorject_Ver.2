import "react-native-gesture-handler";
import "../global.css";

import { useCallback, useEffect, useRef, useState } from "react";
import { DarkTheme, DefaultTheme, ThemeProvider } from "@react-navigation/native";
import { Stack, router, useRootNavigationState } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";
import { AppState, type AppStateStatus } from "react-native";
import "react-native-reanimated";

import { QueryProvider, queryClient } from "@/components/providers/query-provider";
import { hrefBiometricLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { presenceApi } from "@/features/presence/api/presence-api";
import { usePresenceStore } from "@/features/presence/store/presence-store";
import { useAuthBootstrap } from "@/hooks/use-auth-bootstrap";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { AppUpdateManager } from "@/features/app-update/components/AppUpdateManager";

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

  console.log("[Notification] response received", {
    identifier: response.notification.request.identifier,
    data,
    appState: AppState.currentState,
  });

  if (data.type === "direct_message") {
    console.log("[Notification] navigating", {
      type: data.type,
      roomId: data.room_id,
      route: "/(app)/(tabs)/messages",
    });
    router.push({
      pathname: "/(app)/(tabs)/messages",
      params: { roomId: String(data.room_id) },
    });
  }

  if (data.type === "notice") {
    const noticeId = data.notice_id;
    console.log("[Notification] navigating", {
      type: data.type,
      noticeId,
      route: "/(app)/notice/[id]",
    });
    if (noticeId === undefined || noticeId === null) {
      console.warn("[Notification] notice_id is missing", { data });
      return;
    }
    router.push({
      pathname: "/(app)/notice/[id]",
      params: { id: String(noticeId) },
    });
  }

  if (data.type === "cafeteria") {
    const menuDate = typeof data.menu_date === "string" ? data.menu_date : "";
    console.log("[Notification] navigating", {
      type: data.type,
      menuDate,
      route: "/(app)/(tabs)/meal",
    });
    router.push({
      pathname: "/(app)/(tabs)/meal",
      params: menuDate ? { date: menuDate } : undefined,
    });
  }

  if (data.type === "shuttle") {
    const semester = typeof data.semester === "string" ? data.semester : "";
    console.log("[Notification] navigating", {
      type: data.type,
      semester,
      route: "/(app)/(tabs)/shuttle",
    });
    router.push({
      pathname: "/(app)/(tabs)/shuttle",
      params: semester ? { semester } : undefined,
    });
  }
};

export const unstable_settings = {
  initialRouteName: "(app)",
};

const BIOMETRIC_REAUTH_BACKGROUND_MS = 5 * 60 * 1000;

function NavigationTree() {
  const userId = useAuthStore((state) => state.user?.id);
  const authReady = useAuthStore((state) => state.ready);
  const user = useAuthStore((state) => state.user);
  const rootNavigationState = useRootNavigationState();
  const appState = useRef<AppStateStatus>(AppState.currentState);
  const handledNotificationIds = useRef(new Set<string>());
  const [pendingNotification, setPendingNotification] = useState<Notifications.NotificationResponse | null>(null);

  const enqueueNotificationResponse = useCallback((response: Notifications.NotificationResponse) => {
    const notificationId = response.notification.request.identifier;
    if (handledNotificationIds.current.has(notificationId)) return;
    console.log("[Notification] queued", {
      identifier: notificationId,
      data: response.notification.request.content.data,
      appState: AppState.currentState,
    });
    setPendingNotification(response);
  }, []);

  useEffect(() => {
    // 앱 실행 중 또는 백그라운드에서 알림을 누른 경우
    const subscription = Notifications.addNotificationResponseReceivedListener(enqueueNotificationResponse);
    const receivedSubscription = Notifications.addNotificationReceivedListener((notification) => {
      const type = notification.request.content.data.type;
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      if (type === "notice") void queryClient.invalidateQueries({ queryKey: ["notices"] });
      if (type === "direct_message") void queryClient.invalidateQueries({ queryKey: ["chatRooms"] });
    });
    // 앱이 완전히 종료된 상태에서 알림을 눌러 시작된 경우
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) {
        enqueueNotificationResponse(response);
      }
    });

    return () => {
      subscription.remove();
      receivedSubscription.remove();
    };
  }, [enqueueNotificationResponse]);

  useEffect(() => {
    const navigationReady = Boolean(rootNavigationState?.key);
    console.log("[Notification] pending check", {
      pending: pendingNotification?.notification.request.content.data ?? null,
      authReady,
      userId: user?.id ?? null,
      navigationReady,
      navigationKey: rootNavigationState?.key ?? null,
    });
    if (!pendingNotification || !authReady || !user || !navigationReady) return;

    const notificationId = pendingNotification.notification.request.identifier;
    handledNotificationIds.current.add(notificationId);
    setPendingNotification(null);
    console.log("[Notification] processing queued response", {
      identifier: notificationId,
      data: pendingNotification.notification.request.content.data,
    });
    handleNotificationResponse(pendingNotification);
  }, [authReady, pendingNotification, rootNavigationState?.key, user]);

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

  useEffect(() => {
    let backgroundedAt: number | null = null;

    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState !== "active") {
        if (backgroundedAt === null) backgroundedAt = Date.now();
        return;
      }

      const elapsed = backgroundedAt === null ? 0 : Date.now() - backgroundedAt;
      backgroundedAt = null;
      if (elapsed < BIOMETRIC_REAUTH_BACKGROUND_MS) return;

      console.log("[Auth] Background timeout reached", {
        elapsedMs: elapsed,
        thresholdMs: BIOMETRIC_REAUTH_BACKGROUND_MS,
      });
      void useAuthStore.getState().lockForBiometric().then((locked) => {
        if (!locked) return;
        router.replace(hrefBiometricLogin as never);
      });
    });

    return () => subscription.remove();
  }, []);

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
      <AppUpdateManager />
    </QueryProvider>
  );
}
