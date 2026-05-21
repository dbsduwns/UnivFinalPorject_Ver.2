import { Text, View } from "react-native";

import { AppScrollContent } from "@/components/AppScrollContent";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { AppScreenLayout } from "@/components/AppScreenLayout";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <Text className="text-white text-2xl font-bold text-center">This page is for My Info</Text>
      </AppScrollContent>
    </AppScreenLayout>
  );
}
