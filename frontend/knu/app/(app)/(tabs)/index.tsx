import { View, ScrollView } from "react-native";

import { useAuthStore } from "@/features/auth/store/auth-store";
import { HomeHeader } from "@/components/HomeHeader";
import { AIAskBar } from "@/components/AIAskBar";
import { FaqTag } from "@/components/FaqTag";
import { TodaySchedule } from "@/components/TodaySchedule";
import { QuickMenu } from "@/components/QuickMenu";
import { NoticeCard } from "@/components/NoticeCard";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    // ** 해결 해야 할 문제 **
    // 가로 비율이 좁은 경우 잘리는 문제
    <View className="Home flex-1 flex-col bg-['#F3F4F6']">
      <HomeHeader/>
      <View className="Contents" style={{ flex: 12 }}>
        {/* Contents */}
        <ScrollView 
          className="Scroll flex-1 ">
            <View style={{ width: "100%", maxWidth: 720, alignSelf: "center" }}>
              <AIAskBar/>
              <FaqTag/>
              <TodaySchedule/>
              <QuickMenu/>
              <NoticeCard/>
            </View>
        </ScrollView>
      </View>
    </View>
  );
}