import { View, useWindowDimensions } from "react-native";

import { useAuthStore } from "@/features/auth/store/auth-store";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import AllNotice from "@/components/AllNotice";
import { useNotice } from "@/features/notice/hooks/use_notices";

const CONTENT_MAX_WIDTH = 720;

export default function NoticeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { width } = useWindowDimensions();
  const horizontalPadding = width >= 768 ? 32 : 20;
  return (
    <AppScreenLayout>
      <View 
        className="flex-1 w-full"
        style={{
          maxWidth: CONTENT_MAX_WIDTH,
          alignSelf: "center",
          paddingHorizontal: horizontalPadding,
        }}
      >
        <AllNotice />
      </View>
    </AppScreenLayout>
  );
}