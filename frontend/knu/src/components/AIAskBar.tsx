import { Pressable, Text, View, ScrollView, TextInput } from "react-native";
import { Mic, BotMessageSquare } from "lucide-react-native";

export const AIAskBar = () => {
    return (
        // AI Chat Bot
        <View 
        className="ChatWrapper flex-row mx-5 mt-5 bg-white justify-center items-center"
        style={{
            borderWidth: 2,
            borderColor: '#E5E7EB',
            borderRadius: 15
        }}>
            <View 
                className="BotIconWrapper ml-4" 
                style={{ flexDirection: "row" }}>
                <BotMessageSquare color={ "#13708d" } />
            </View>
            {/* TextInput */} 
            <View className="TextinputWrapper" style={{ flex: 15 }}>
                <TextInput 
                className="px-4"
                placeholder="무엇이든 물어보세요 ..."
                />
            </View>
            {/* STT (Speech To Text ) */}
            <View className="MicWrapper" style={{ flex: 1, flexDirection: "row" }}>
                <Mic color={ "#13708d" } />
            </View>
        </View>
    )
}