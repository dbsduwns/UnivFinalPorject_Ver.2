import { Stack } from "expo-router";

import { AppDrawerProvider } from "@/components/AppDrawer";

export default function AppGroupLayout() {
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
