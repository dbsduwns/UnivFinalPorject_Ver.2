import { View } from "react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import AllNotice from "@/features/notice/componenets/AllNotice";

export default function NoticeScreen() {
  return (
    <AppScreenLayout>
      <View className="flex-1 w-full">
        <AllNotice />
      </View>
    </AppScreenLayout>
  );
}
