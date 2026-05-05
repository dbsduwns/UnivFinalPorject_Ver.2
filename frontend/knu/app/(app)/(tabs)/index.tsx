import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { googleLoginRequest } from "@/features/auth/api/auth";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <View className="flex-1 justify-center items-center bg-blue-500 px-4">
      <Text className="text-white text-2xl font-bold text-center">KNU Campus Life!</Text>
      {user ? (
        <Text className="text-blue-100 mt-2 text-center">
          {user.name}님 ({user.email})
        </Text>
      ) : null}
      <Pressable
        className="mt-6 rounded-lg bg-white/20 px-4 py-3 active:opacity-80"
        onPress={async () => {
          await logout();
          router.replace(hrefLogin);
        }}
      >
        <Text className="text-center text-white font-medium">로그아웃</Text>
      </Pressable>
    </View>
  );
}
