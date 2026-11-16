import { useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
import { Fingerprint, X } from "lucide-react-native";
import { useAuthStore } from "@/features/auth/store/auth-store";

type PasswordVerificationProps = {
    onVerified: (usedBiometric?: boolean) => void;
    onClose: () => void;
}

export default function PasswordVerificationForm({ onVerified, onClose, }: PasswordVerificationProps) {

    const insets = useSafeAreaInsets();

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const unlockWithBiometric = useAuthStore((state) => state.unlockWithBiometric);

    const handleBiometricAuth = async () => {
        try {
            setLoading(true);
            const unlocked = await unlockWithBiometric();
            if (!unlocked) {
                setError("생체 인증 로그인을 먼저 설정해주세요.");
                return;
            }
            onVerified(true);
        } catch {
            setError("생체 인증에 실패했습니다. 다시 시도해주세요.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <View className="flex-1 bg-white">
            {/* 헤더 */}
            <View
                className="flex-row items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100"
                style={{ paddingTop: insets.top, height: insets.top + 76 }}
            >
                <Text className="text-xl font-bold text-gray-900">회원 정보 수정</Text>
                <TouchableOpacity 
                    className="items-center justify-center"
                    onPress={onClose}
                >
                    <X size={25} color="#4B5563" />
                </TouchableOpacity>
            </View>

            <View className="flex-1">
                <View className="flex-1 items-center justify-center px-6">
                    <Fingerprint size={64} color="#2563EB" />
                    <Text className="mt-6 text-center text-xl font-bold text-gray-900">
                        생체 인증이 필요합니다
                    </Text>
                    <Text className="mt-3 text-center leading-6 text-gray-500">
                        회원 정보 수정은 등록된 지문 또는 얼굴 인증으로만 본인 확인할 수 있습니다.
                    </Text>
                    {error ? <Text className="mt-4 text-center text-sm text-red-600">{error}</Text> : null}
                </View>
            </View>

            {/* 저장 버튼 */}
            <View
                className="border-t border-gray-100"
                style={{ paddingBottom: Math.max(insets.bottom, 20), elevation: 4 }}
            >
                <TouchableOpacity
                onPress={() => void handleBiometricAuth()}
                disabled={loading}
                className={`flex-row py-4 items-center justify-center ${loading ? 'bg-blue-300' : 'bg-blue-600'}`}
                >
                {loading ? (
                    <ActivityIndicator color="white" />
                ) : (
                    <>
                        <Fingerprint size={21} color="white" />
                        <Text className="ml-2 text-white font-bold text-lg">생체 인증하기</Text>
                    </>
                )}
                </TouchableOpacity>
            </View>
        </View>
    )
}
