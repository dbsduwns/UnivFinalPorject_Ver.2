import { useState, useCallback } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { View, Text, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, Alert, ActivityIndicator } from "react-native";
import { X, Key } from "lucide-react-native";
import { verifyPassword } from "@/features/auth/api/auth";

type PasswordVerificationProps = {
    onVerified: () => void;
    onClose: () => void;
}

export default function PasswordVerificationForm({ onVerified, onClose, }: PasswordVerificationProps) {

    const insets = useSafeAreaInsets();

    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSave = async () => {
        try {
            setLoading(true);
            await verifyPassword({password});
            Alert.alert("인증되었습니다.");
            onVerified();
        } catch {
            setError("비밀번호가 일치하지 않습니다.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <View className="flex-1 bg-white">
            {/* 헤더 */}
            <View className="flex-row items-center justify-between mt-10 px-6 pt-6 pb-4 border-b border-gray-100">
                <Text className="text-xl font-bold text-gray-900">회원 정보 수정</Text>
                <TouchableOpacity 
                    className="items-center justify-center"
                    onPress={onClose}
                >
                    <X size={25} color="#4B5563" />
                </TouchableOpacity>
            </View>

            <KeyboardAvoidingView 
                behavior={Platform.OS === "ios" ? "padding" : "height"}
                className="flex-1"
            >
                <ScrollView className="flex-1 px-6 pt-6">
                {/* 학번 */}
                <View className="mb-6">
                    <View className="flex-row items-center mb-2">
                    <Key size={18} color="#4B5563" />
                    <Text className="ml-2 font-bold text-gray-700">비밀번호</Text>
                    </View>
                    <TextInput
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                    autoCapitalize="none"
                    placeholder="현재 비밀번호"
                    className="bg-gray-50 px-4 py-4 rounded-2xl border border-gray-200 text-gray-900"
                    />
                    {error ? (<Text>{error}</Text>) : (
                        <Text className="text-gray-400 text-s mt-2 ml-1">
                        사용자 인증을 위해 비밀번호를 입력해주세요.
                        </Text>
                    )}
                </View>

                <View className="h-20" />
                </ScrollView>
            </KeyboardAvoidingView>

            {/* 저장 버튼 */}
            <View
                className="border-t border-gray-100"
                style={{ paddingBottom: Math.max(insets.bottom, 20), elevation: 4 }}
            >
                <TouchableOpacity
                onPress={handleSave}
                disabled={loading}
                className={`py-4 items-center justify-center ${loading ? 'bg-blue-300' : 'bg-blue-600'}`}
                >
                {loading ? (
                    <ActivityIndicator color="white" />
                ) : (
                    <Text className="text-white font-bold text-lg">저장하기</Text>
                )}
                </TouchableOpacity>
            </View>
        </View>
    )
}
