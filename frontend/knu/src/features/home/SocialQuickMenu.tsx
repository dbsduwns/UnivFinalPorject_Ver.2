import type { DimensionValue } from "react-native";
import { router } from "expo-router";
import { Pressable, Text, View, useWindowDimensions } from "react-native";
import { BusFront, Utensils, MapPin, Megaphone } from "lucide-react-native";

export const SocialQuickMenu = () => {
    const { width } = useWindowDimensions();

    const columns = width >= 360 ? 4 : 2;
    const itemWidth = `${100 / columns}%` as DimensionValue;

    const iconWidth = Math.min(Math.max(width * 0.2, 65), 140); // 아이콘 너비
    const iconHeight = iconWidth * 0.6;  // 아이콘 높이
    const iconRadius =  iconHeight / 3; // 아이콘 테두리 반지름
    const iconColor = '#13708D'; // 아이콘 색상
    const iconBgColor = '#E5E7EB'; // 아이콘 테두리 색상


    return (

        <View>
            <View
                className="felx-row pb-4"

            >
                <Text
                    style={{ fontSize: 20, fontWeight: "600" }}>
                    캠퍼스 생활
                </Text>
            </View>
            <View
            className="QuickMenu justify-center flex-row flex-wrap"
            style={{ width: "100%", rowGap: 16, gap: 8 }}>
            {/* Shuttle Button */}
                <View
                    style={{
                        alignItems: "center",
                        justifyContent: "center",
                        borderWidth: 1,
                        borderRadius: iconRadius,
                        borderColor: iconBgColor,
                    }}>
                    <Pressable 
                        style={{ alignItems: "center" }}
                        onPress={() => router.push("/(app)/(tabs)/shuttle")}>
                        <View 
                            className="ShuttleQuickMenu items-center p-4 flex-row"
                            style={{
                                backgroundColor: '#FFFFFF',
                                borderRadius: iconRadius,
                                width: iconWidth,
                                height: iconHeight
                            }}>
                            <BusFront 
                                size={20}
                                color={iconColor}/>
                            <Text style={{ fontWeight: 'bold', color: iconColor, marginLeft: "auto" }}>셔틀</Text>
                        </View>
                    </Pressable>
                </View>
            
            {/* Meal Button */}
                <View
                    style={{
                        alignItems: "center",
                        justifyContent: "center",
                        borderWidth: 1,
                        borderRadius: iconRadius,
                        borderColor: iconBgColor,
                    }}>
                    <Pressable 
                        style={{ alignItems: "center" }}
                        onPress={() => router.push("/(app)/(tabs)/meal")}>
                        <View 
                            className="MealQuickMenu items-center p-4 flex-row"
                            style={{
                                backgroundColor: '#FFFFFF',
                                borderRadius: iconRadius,
                                width: iconWidth,
                                height: iconHeight
                            }}>
                            <Utensils 
                                size={20}
                                color={iconColor}/>
                            <Text style={{ fontWeight: 'bold', color: iconColor, marginLeft: "auto" }}>학식</Text>
                        </View>
                    </Pressable>
                </View>
            {/* Campus Map Button */}
                <View
                    style={{
                        alignItems: "center",
                        justifyContent: "center",
                        borderWidth: 1,
                        borderRadius: iconRadius,
                        borderColor: iconBgColor,
                    }}>
                    <Pressable 
                        style={{ alignItems: "center" }}
                        onPress={() => router.push("/(app)/(tabs)/campus-map")}>
                        <View 
                            className="CampusMapQuickMenu items-center p-4 flex-row"
                            style={{
                                backgroundColor: '#FFFFFF',
                                borderRadius: iconRadius,
                                width: iconWidth,
                                height: iconHeight
                            }}>
                            <MapPin
                                size={20}
                                color={iconColor}/>
                            <Text style={{ fontWeight: 'bold', color: iconColor, marginLeft: "auto" }}>캠퍼스맵</Text>
                        </View>
                    </Pressable>
                </View>
            {/* Notification Button */}
                <View
                    style={{
                        alignItems: "center",
                        justifyContent: "center",
                        borderWidth: 1,
                        borderRadius: iconRadius,
                        borderColor: iconBgColor,
                    }}>
                    <Pressable 
                        style={{ alignItems: "center" }}
                        onPress={() => router.push("/(app)/(tabs)/notice")}>
                        <View 
                            className="NotificationQuickMenu items-center p-4 flex-row"
                            style={{
                                backgroundColor: '#FFFFFF',
                                borderRadius: iconRadius,
                                width: iconWidth,
                                height: iconHeight
                            }}>
                            <Megaphone 
                                size={20}
                                color={iconColor}/>
                            <Text style={{ fontWeight: 'bold', color: iconColor, marginLeft: "auto" }}>공지</Text>
                        </View>
                    </Pressable>
                </View>
            </View>
        </View>
        
    )
}
