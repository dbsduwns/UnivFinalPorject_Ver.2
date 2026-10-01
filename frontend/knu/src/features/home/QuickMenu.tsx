import type { DimensionValue } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, Text, View, useWindowDimensions } from "react-native";
import { MessageCircle, Megaphone, Calendar } from "lucide-react-native";

import { getFriendRequests } from "@/features/friend/api/friend";

export const QuickMenu = () => {
    const { width } = useWindowDimensions();
    const { data: friendRequests } = useQuery({
        queryKey: ["friendRequests"],
        queryFn: getFriendRequests,
    });
    const pendingRequestCount = friendRequests?.received?.length ?? 0;

    const columns = width >= 360 ? 4 : 2;
    const itemWidth = `${100 / columns}%` as DimensionValue;

    const iconSize = 35; // 아이콘 크기 조정
    const iconColor = '#13708D'; // 아이콘 색상
    const iconBgColor = '#EAF8FC'; // 아이콘 배경색

    return (

        <View>
            {/* Quick Menu Title */}
            <View
                className="QuickMenuTitle"
                style={{ paddingBottom: 16, flexDirection: "row" }}>
                <Text
                    style={{ fontSize: 20, fontWeight: "600" }}>
                    함께하는 캠퍼스
                </Text>
                <Pressable
                    onPress={() => router.push("/(app)/messages")}
                    style={{ marginLeft: "auto" }}
                >
                    <Text style={{ color: pendingRequestCount > 0 ? "#DC2626" : "#6B7280" }}>
                        친구 요청 {pendingRequestCount}
                    </Text>
                </Pressable>
            </View>
            {/* Quick Menu Items [ Shuttle / Restaurant / Campus Map / Schedule ] */}
            <View
                className="QuickMenu justify-center flex-row flex-wrap"
                style={{ width: "100%", rowGap: 16 }}>
                {/* Restraurant Menu Button */}
                <View
                    style={{
                        width: itemWidth,
                        alignItems: "center",
                    }}>
                    <Pressable 
                        style={{ alignItems: "center" }}
                        onPress={() => router.push("/(app)/messages")}>
                        <View 
                            className="items-center p-4"
                            style={{
                                backgroundColor: iconBgColor,
                                borderRadius: 20,
                            }}>
                            <MessageCircle
                                size={iconSize}
                                color={iconColor}/>
                        </View>
                        <View className="items-center pt-5">
                            <Text style={{ fontWeight: 'bold' }}>쪽지</Text>
                        </View>
                    </Pressable>
                </View>
                {/* Campus Map Button */}
                <View
                    style={{
                        width: itemWidth,
                        minWidth: 64,
                        alignItems: "center",
                    }}>
                    <Pressable 
                        style={{ width: "100%", alignItems: "center" }}
                        onPress={() => router.push("/(app)/(tabs)/community")}>
                        <View
                            className="items-center p-4"
                            style={{
                                backgroundColor: iconBgColor,
                                borderRadius: 20,
                            }}>
                            <Megaphone
                                size={iconSize}
                                color={iconColor}/>
                        </View>
                        <View className="items-center pt-5">
                            <Text style={{ fontWeight: 'bold' }}>커뮤니티</Text>
                        </View>
                    </Pressable>
                </View>
                {/* Schedule Button */}
                <View
                    style={{
                        width: itemWidth,
                        minWidth: 64,
                        alignItems: "center",
                    }}>
                    <Pressable 
                        style={{ width: "100%", alignItems: "center"}}
                        onPress={() => router.push("/(app)/(tabs)/schedule")}>
                        <View 
                            className="items-center p-4"
                            style={{
                                backgroundColor: iconBgColor,
                                borderRadius: 20,
                            }}>
                            <Calendar
                                size={iconSize}
                                color={iconColor}/>
                        </View>
                        <View className="items-center pt-5">
                            <Text style={{ fontWeight: 'bold' }}>시간표</Text>
                        </View>
                    </Pressable>
                </View>
            </View>
            
        </View>
    )
}
