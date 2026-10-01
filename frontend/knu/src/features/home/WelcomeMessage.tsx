import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { Megaphone, ChevronRight } from "lucide-react-native";
import { Notice } from "@/features/auth/api/types";
import { useAuthStore } from "@/features/auth/store/auth-store";


export const WelcomeMessage = () => {

    const user = useAuthStore(s => s.user);

    // 오늘 요일 가져오기
    const getTodayDayOfWeek = () => {
        const days = [ "일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일" ];
        return days[new Date().getDay()];
    };

    return (
        <View>
            <Text
                style={{
                fontSize: 25,
                fontWeight: "bold",

                }}>
                안녕하세요, {user ? user.name : "사용자"}님 👋
            </Text>
            <Text style={{ color: "#6B7280" }}>
                {getTodayDayOfWeek()} 일정과 캠퍼스 소식을 한눈에 확인하세요
            </Text>
        </View>
    )
}