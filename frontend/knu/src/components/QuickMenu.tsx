import { Pressable, Text, View, ScrollView, TextInput, useWindowDimensions } from "react-native";
import { Calendar, BusFront, MapPin, Utensils } from "lucide-react-native";

export const QuickMenu = () => {

    /*
    const { width } = useWindowDimensions;

    const columns = width >= 768 ? 4 : width >= 420 ? 4 : 2;
    const itemwidth = `${100 / columns - 3}%`;
    */

    return (
        // Quick Menu Button

        <View
            className="QuickMenu justify-center flex-row mx-5 mt-12 ">
            {/* Shuttle Button */}
            <View
                style={{
                    width: "23%",
                    minWidth: 64,
                    alignItems: "center",
                    marginBottom: 16,
                }}>
                <Pressable>
                    <View className="ShuttleQuickMenu items-center">
                        <BusFront size={50}/>
                    </View>
                    <View className="items-center">
                        <Text>셔틀</Text>
                    </View>
                </Pressable>
            </View>
            {/* Restraurant Menu Button */}
            <View
                style={{
                    width: "23%",
                    minWidth: 64,
                    alignItems: "center",
                    marginBottom: 16,
                }}>
                <Pressable>
                    <View className="items-center">
                        <Utensils size={50}/>
                    </View>
                    <View className="items-center">
                        <Text>학식</Text>
                    </View>
                </Pressable>
            </View>
            {/* Campus Map Button */}
            <View
                style={{
                    width: "23%",
                    minWidth: 64,
                    alignItems: "center",
                    marginBottom: 16,
                }}>
                <Pressable>
                    <View className="items-center">
                        <MapPin size={50}/>
                    </View>
                    <View className="items-center">
                        <Text>캠퍼스맵</Text>
                    </View>
                </Pressable>
            </View>
            {/* Schedule Button */}
            <View
                style={{
                    width: "23%",
                    minWidth: 64,
                    alignItems: "center",
                    marginBottom: 16,
                }}>
                <Pressable>
                    <View className="items-center">
                        <Calendar size={50}/>
                    </View>
                    <View className="items-center">
                        <Text>시간표</Text>
                    </View>
                </Pressable>
            </View>
        </View>
    )
}