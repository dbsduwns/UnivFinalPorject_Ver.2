import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <View className="flex-1 justify-center items-center bg-blue-500 px-4">
      <Text className="text-white text-2xl font-bold text-center">This page is for My Info</Text>
    </View>
  );
}
