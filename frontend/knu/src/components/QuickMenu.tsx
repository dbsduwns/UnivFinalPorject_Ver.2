import type { DimensionValue } from "react-native";
import { router } from "expo-router";
import { Pressable, Text, View, useWindowDimensions } from "react-native";
import { Calendar, BusFront, MapPin, Utensils } from "lucide-react-native";

export const QuickMenu = () => {
    const { width } = useWindowDimensions();

    const columns = width >= 360 ? 4 : 2;
    const itemWidth = `${100 / columns}%` as DimensionValue;

    return (
        // Quick Menu Button

        <View
            className="QuickMenu justify-center flex-row flex-wrap"
            style={{ width: "100%", rowGap: 16 }}>
            {/* Shuttle Button */}
            <View
                style={{
                    width: itemWidth,
                    minWidth: 64,
                    alignItems: "center",
                }}>
                <Pressable 
                    style={{ width: "100%", alignItems: "center" }}
                    onPress={() => router.push("/(app)/(tabs)/shuttle")}>
                    <View 
                        className="ShuttleQuickMenu items-center p-4"
                        style={{
                            backgroundColor: '#1aaedb',
                            borderRadius: 20,
                        }}>
                        <BusFront 
                            size={50}
                            color={'white'}/>
                    </View>
                    <View className="items-center pt-5">
                        <Text style={{ fontWeight: 'bold' }}>셔틀</Text>
                    </View>
                </Pressable>
            </View>
            {/* Restraurant Menu Button */}
            <View
                style={{
                    width: itemWidth,
                    minWidth: 64,
                    alignItems: "center",
                }}>
                <Pressable 
                    style={{ width: "100%", alignItems: "center" }}
                    onPress={() => router.push("/(app)/(tabs)/meal")}>
                    <View 
                        className="items-center p-4"
                        style={{
                            backgroundColor: '#F59E0B',
                            borderRadius: 20,
                        }}>
                        <Utensils
                            size={50}
                            color={'white'}/>
                    </View>
                    <View className="items-center pt-5">
                        <Text style={{ fontWeight: 'bold' }}>학식</Text>
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
                    onPress={() => router.push("/(app)/(tabs)/campus-map")}>
                    <View
                        className="items-center p-4"
                        style={{
                            backgroundColor: '#10B981',
                            borderRadius: 20,
                        }}>
                        <MapPin
                            size={50}
                            color={'white'}/>
                    </View>
                    <View className="items-center pt-5">
                        <Text style={{ fontWeight: 'bold' }}>캠퍼스맵</Text>
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
                            backgroundColor: '#8B5CF6',
                            borderRadius: 20,
                        }}>
                        <Calendar
                            size={50}
                            color={'white'}/>
                    </View>
                    <View className="items-center pt-5">
                        <Text style={{ fontWeight: 'bold' }}>시간표</Text>
                    </View>
                </Pressable>
            </View>
        </View>
    )
}
