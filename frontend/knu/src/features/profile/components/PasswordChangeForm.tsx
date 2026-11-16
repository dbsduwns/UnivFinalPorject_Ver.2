import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Fingerprint, X } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import { changePassword } from "@/features/auth/api/auth";
import { useAuthStore } from "@/features/auth/store/auth-store";

type PasswordChangeFormProps = { onClose: () => void; onChanged: () => void };

export default function PasswordChangeForm({ onClose, onChanged }: PasswordChangeFormProps) {
  const insets = useSafeAreaInsets();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [biometricVerified, setBiometricVerified] = useState(false);
  const unlockWithBiometric = useAuthStore((state) => state.unlockWithBiometric);

  async function handleChangePassword() {
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("새 비밀번호와 비밀번호 재입력이 일치하지 않습니다.");
      return;
    }
    if (!biometricVerified && newPassword === currentPassword) {
      setError("새 비밀번호는 현재 비밀번호와 달라야 합니다.");
      return;
    }

    setLoading(true);
    try {
      await changePassword({
        current_password: biometricVerified ? undefined : currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
        biometric_auth: biometricVerified,
      });
      onChanged();
    } catch (cause) {
      setError(getAxiosErrorMessage(cause, "비밀번호 변경에 실패했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function handleBiometricAuth() {
    setError(null);
    try {
      setLoading(true);
      const unlocked = await unlockWithBiometric();
      if (!unlocked) {
        setError("생체 인증 로그인을 먼저 설정해주세요.");
        return;
      }
      setBiometricVerified(true);
      setCurrentPassword("");
    } catch {
      setError("생체 인증에 실패했습니다. 비밀번호로 인증해주세요.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? insets.top : 0}
    >
      <View className="flex-1" style={{ paddingTop: insets.top }}>
        <View className="flex-row items-center justify-between border-b border-gray-100 px-6 py-4">
          <Text className="text-xl font-bold text-gray-900">비밀번호 변경</Text>
          <TouchableOpacity accessibilityLabel="닫기" onPress={onClose} className="p-2">
            <X size={22} color="#4B5563" />
          </TouchableOpacity>
        </View>

        <ScrollView
          className="flex-1 px-6 pt-6"
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ paddingBottom: 24 }}
        >
          {!biometricVerified && <PasswordField label="현재 비밀번호" value={currentPassword} onChangeText={setCurrentPassword} />}
          {biometricVerified && <Text className="mb-5 rounded-2xl bg-green-50 px-4 py-4 text-sm font-bold text-green-700">생체 인증으로 본인 확인이 완료되었습니다.</Text>}
          <PasswordField label="변경할 비밀번호" value={newPassword} onChangeText={setNewPassword} />
          <PasswordField label="새 비밀번호 재입력" value={confirmPassword} onChangeText={setConfirmPassword} />
          <Text className="mb-4 text-xs text-gray-500">비밀번호는 8자 이상이어야 합니다.</Text>
          {!biometricVerified && (
            <Pressable onPress={() => void handleBiometricAuth()} disabled={loading} className="mb-4 flex-row items-center justify-center rounded-2xl border border-blue-200 py-3">
              <Fingerprint size={19} color="#2563EB" />
              <Text className="ml-2 font-bold text-blue-600">지문·생체 인증으로 현재 비밀번호 확인</Text>
            </Pressable>
          )}
          {error ? <Text accessibilityRole="alert" className="mb-4 text-sm text-red-600">{error}</Text> : null}
        </ScrollView>

        <View className="border-t border-gray-100 px-6 pt-4" style={{ paddingBottom: Math.max(insets.bottom, 20) }}>
          <Pressable
            onPress={() => void handleChangePassword()}
            disabled={loading || (!biometricVerified && !currentPassword) || !newPassword || !confirmPassword}
            className={`items-center justify-center rounded-2xl py-4 ${loading ? "bg-blue-300" : "bg-blue-600"}`}
          >
            {loading ? <ActivityIndicator color="white" /> : <Text className="text-lg font-bold text-white">비밀번호 변경</Text>}
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function PasswordField({ label, value, onChangeText }: { label: string; value: string; onChangeText: (value: string) => void }) {
  return (
    <View className="mb-5">
      <Text className="mb-2 font-bold text-gray-700">{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="newPassword"
        placeholder={label}
        className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-gray-900"
      />
    </View>
  );
}
