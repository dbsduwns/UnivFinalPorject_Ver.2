import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, TextInput, TouchableOpacity, View } from "react-native";
import { Audio } from "expo-av";
import { useRouter } from "expo-router";
import { BotMessageSquare, Mic, SendHorizonal, StopCircle } from "lucide-react-native";
import * as FileSystem from "expo-file-system/legacy";

// Korean speech recognition model. The base model is about 140 MB.
const MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin";
const WHISPER_DIR = `${FileSystem.documentDirectory}whisper/`;
const MODEL_PATH = `${WHISPER_DIR}ggml-base.bin`;
const MIN_MODEL_SIZE_BYTES = 100 * 1024 * 1024;

export const AIAskBar = () => {
    const [text, setText] = useState("");
    const [isListening, setIsListening] = useState(false);
    const [isInitializing, setIsInitializing] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const recordingRef = useRef<Audio.Recording | null>(null);
    const router = useRouter();

    const handleSend = () => {
        if (!text.trim()) return;
        router.push({
            pathname: "/(app)/(tabs)/ai_chat",
            params: { q: text.trim() },
        });
        setText("");
    };

    return (
        <View
            className="ChatWrapper flex-row bg-white justify-center items-center"
            style={{
                borderWidth: 2,
                borderColor: "#E5E7EB",
                borderRadius: 15,
                width: "100%",
            }}
        >
            <View className="BotIconWrapper ml-4">
                <BotMessageSquare color="#13708d" />
            </View>

            <View className="TextinputWrapper" style={{ flex: 15 }}>
                <TextInput
                    className="px-4 h-12"
                    placeholder={
                        isInitializing
                            ? "모델을 준비하는 중..."
                            : isTranscribing
                              ? "음성을 텍스트로 변환하는 중..."
                              : "무엇이든 물어보세요..."
                    }
                    value={text}
                    onChangeText={setText}
                    onSubmitEditing={handleSend}
                    editable={!isListening && !isTranscribing}
                />
            </View>

            <TouchableOpacity className="Sendrapper p-2" onPress={handleSend}>
                <SendHorizonal color="#13708d" />
            </TouchableOpacity>
        </View>
    );
};
