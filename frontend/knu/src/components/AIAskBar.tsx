import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, TextInput, TouchableOpacity, View } from "react-native";
import { Audio } from "expo-av";
import { useRouter } from "expo-router";
import { BotMessageSquare, Mic, SendHorizonal, StopCircle } from "lucide-react-native";
import * as FileSystem from "expo-file-system/legacy";
import { initWhisper, type WhisperContext } from "whisper.rn";

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
    const whisperContext = useRef<WhisperContext | null>(null);
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

    const initializeWhisper = async () => {
        if (whisperContext.current) return whisperContext.current;

        try {
            setIsInitializing(true);

            const dirInfo = await FileSystem.getInfoAsync(WHISPER_DIR);
            if (!dirInfo.exists) {
                await FileSystem.makeDirectoryAsync(WHISPER_DIR, { intermediates: true });
            }

            const fileInfo = await FileSystem.getInfoAsync(MODEL_PATH);
            if (fileInfo.exists && "size" in fileInfo && fileInfo.size < MIN_MODEL_SIZE_BYTES) {
                await FileSystem.deleteAsync(MODEL_PATH, { idempotent: true });
            }

            const modelInfo = await FileSystem.getInfoAsync(MODEL_PATH);
            if (!modelInfo.exists) {
                console.log("Downloading Whisper model via legacy API...");
                await FileSystem.downloadAsync(MODEL_URL, MODEL_PATH);
            }

            const context = await initWhisper({ filePath: MODEL_PATH });
            whisperContext.current = context;
            return context;
        } catch (error) {
            console.error("Whisper initialization failed:", error);
            Alert.alert("오류", "음성 인식 모델을 불러오지 못했습니다.");
            return null;
        } finally {
            setIsInitializing(false);
        }
    };

    const startRecording = async () => {
        const context = await initializeWhisper();
        if (!context) return;

        const permission = await Audio.requestPermissionsAsync();
        if (!permission.granted) {
            Alert.alert("마이크 권한 필요", "질문을 듣기 위해 마이크 권한이 필요합니다.");
            return;
        }

        try {
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });

            const { recording } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.HIGH_QUALITY
            );
            recordingRef.current = recording;
            setIsListening(true);
        } catch (error) {
            console.error("Recording start failed:", error);
            setIsListening(false);
            Alert.alert("오류", "녹음을 시작하지 못했습니다.");
        }
    };

    const stopRecordingAndTranscribe = async () => {
        const recording = recordingRef.current;
        const context = whisperContext.current;

        if (!recording || !context) {
            setIsListening(false);
            return;
        }

        try {
            setIsListening(false);
            setIsTranscribing(true);

            await recording.stopAndUnloadAsync();
            const audioUri = recording.getURI();
            recordingRef.current = null;

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
            });

            if (!audioUri) {
                Alert.alert("오류", "녹음 파일을 찾지 못했습니다.");
                return;
            }

            const { promise } = context.transcribe(audioUri, { language: "ko" });
            const result = await promise;
            if (result.result) {
                setText(result.result.trim());
            }
        } catch (error) {
            console.error("Transcription failed:", error);
            Alert.alert("오류", "음성을 텍스트로 변환하지 못했습니다.");
        } finally {
            setIsTranscribing(false);
            recordingRef.current = null;
        }
    };

    const toggleListening = async () => {
        if (isInitializing || isTranscribing) return;

        if (isListening) {
            await stopRecordingAndTranscribe();
        } else {
            await startRecording();
        }
    };

    useEffect(() => {
        return () => {
            if (recordingRef.current) {
                recordingRef.current.stopAndUnloadAsync();
            }
            if (whisperContext.current) {
                whisperContext.current.release();
            }
        };
    }, []);

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

            <TouchableOpacity
                className="MicWrapper p-2 mr-2"
                onPress={toggleListening}
                disabled={isInitializing || isTranscribing}
            >
                {isInitializing || isTranscribing ? (
                    <ActivityIndicator size="small" color="#13708d" />
                ) : isListening ? (
                    <StopCircle color="#ef4444" />
                ) : (
                    <Mic color="#13708d" />
                )}
            </TouchableOpacity>
        </View>
    );
};
