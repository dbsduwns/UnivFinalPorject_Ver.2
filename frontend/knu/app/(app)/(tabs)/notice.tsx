import { View, useWindowDimensions } from "react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import AllNotice from "@/features/notice/componenets/AllNotice";

const CONTENT_MAX_WIDTH = 720;

export default function NoticeScreen() {
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
