import { Stack } from "expo-router";
import { useEffect, useRef } from "react";

import { AppDrawerProvider } from "@/components/AppDrawer";
import { registerForPushNotificationsAsync, sendPushTokenToServer } from "@/utils/notification";
import { useAuthStore } from "@/features/auth/store/auth-store";

export default function AppGroupLayout() {
  const ran = useRef(false);
  const user = useAuthStore(state => state.user);
  const ready = useAuthStore(state => state.ready);

  useEffect(() => {
    if (!ready || !user || ran.current) return;
    ran.current = true;

    registerForPushNotificationsAsync().then(token => {
      if (token) sendPushTokenToServer(token);
    });
  }, [ready, user]);

  return (
    <AppDrawerProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="shuttle" />
        <Stack.Screen name="meal" />
        <Stack.Screen name="campus-map" />
      </Stack>
    </AppDrawerProvider>
  );
}