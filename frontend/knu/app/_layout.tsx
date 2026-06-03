import "react-native-gesture-handler";
import "../global.css";

import { DarkTheme, DefaultTheme, ThemeProvider } from "@react-navigation/native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";
import "react-native-reanimated";

import { QueryProvider } from "@/components/providers/query-provider";
import { useAuthBootstrap } from "@/hooks/use-auth-bootstrap";
import { useColorScheme } from "@/hooks/use-color-scheme";

// 앱 최상단에서 포그라운드 알림 핸들러 등록
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export const unstable_settings = {
  initialRouteName: "(app)/(tabs)",
};

function NavigationTree() {
  useAuthBootstrap();
  const colorScheme = useColorScheme();

  return (
    <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(app)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: "modal", title: "Modal" }} />
      </Stack>
      <StatusBar style="auto" />
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