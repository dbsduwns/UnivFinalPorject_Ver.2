import { useState } from "react";
import { View, TextInput, TouchableOpacity } from "react-native";
import { Mic, BotMessageSquare, SendHorizonal } from "lucide-react-native";
import { useRouter } from "expo-router";

export const AIAskBar = () => {
    const [text, setText] = useState("");
    const router = useRouter();

    const handleSend = () => {
        if (!text.trim()) return;
        // ai_chat 탭으로 이동하며 query 파라미터 전달
        router.push({
            pathname: "/(app)/(tabs)/ai_chat",
            params: { q: text.trim() }
        });
        setText(""); // 입력창 초기화
    };

    return (
        // AI Chat Bot
        <View 
        className="ChatWrapper flex-row bg-white justify-center items-center"
        style={{
            borderWidth: 2,
            borderColor: '#E5E7EB',
            borderRadius: 15,
            width: "100%",
        }}>
            <View 
                className="BotIconWrapper ml-4" 
                style={{ flexDirection: "row" }}>
                <BotMessageSquare color={ "#13708d" } />
            </View>
            {/* TextInput */} 
            <View className="TextinputWrapper" style={{ flex: 15 }}>
                <TextInput 
                className="px-4 h-12"
                placeholder="무엇이든 물어보세요 ..."
                value={text}
                onChangeText={setText}
                onSubmitEditing={handleSend}
                />
            </View>
            {/* Send Button */}
            <TouchableOpacity className="Sendrapper p-2" onPress={handleSend}>
                <SendHorizonal color={ "#13708d" } />
            </TouchableOpacity>
            {/* STT (Speech To Text ) */}
            <View className="MicWrapper p-2 mr-2">
                <Mic color={ "#13708d" } />
            </View>
        </View>
    )
}
