import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { confirmAccountStudentVerification, requestAccountStudentVerification } from "@/features/auth/api/auth";

export default function AccountStudentVerificationScreen() {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationId, setVerificationId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestCode() {
    setLoading(true); setError(null);
    try {
      const result = await requestAccountStudentVerification(email.trim());
      setVerificationId(result.verification_id);
      Alert.alert("인증 코드 발송", "강남대학교 이메일의 받은편지함을 확인해 주세요.");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "인증 코드 발송에 실패했습니다.");
    } finally { setLoading(false); }
  }

  async function confirmCode() {
    if (verificationId === null) return;
    setLoading(true); setError(null);
    try {
      await confirmAccountStudentVerification(verificationId, otp.trim());
      Alert.alert("학생 인증 완료", "학생 인증이 완료되었습니다.", [
        { text: "확인", onPress: () => router.back() },
      ]);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "인증 코드가 올바르지 않습니다.");
    } finally { setLoading(false); }
  }

  return (
    <View className="flex-1 bg-white px-6 pt-20 dark:bg-neutral-950">
      <Text className="text-2xl font-bold text-neutral-900 dark:text-white">학생 인증</Text>
      <Text className="mt-2 text-sm text-neutral-500">강남대학교 이메일로 학생 신분을 인증합니다.</Text>
      {error ? <Text className="mt-5 rounded-lg bg-red-100 p-3 text-red-700">{error}</Text> : null}
      <TextInput className="mt-8 rounded-lg border border-neutral-200 px-3 py-3" autoCapitalize="none" keyboardType="email-address" placeholder="학번@kangnam.ac.kr" value={email} onChangeText={setEmail} />
      <Pressable className="mt-4 items-center rounded-lg bg-[#0a7ea4] py-3" disabled={loading || !email.trim()} onPress={() => void requestCode()}>
        {loading && verificationId === null ? <ActivityIndicator color="#fff" /> : <Text className="font-semibold text-white">인증 코드 받기</Text>}
      </Pressable>
      {verificationId !== null ? <>
        <TextInput className="mt-6 rounded-lg border border-neutral-200 px-3 py-3" keyboardType="number-pad" maxLength={6} placeholder="123456" value={otp} onChangeText={setOtp} />
        <Pressable className="mt-4 items-center rounded-lg bg-[#0a7ea4] py-3" disabled={loading || otp.length !== 6} onPress={() => void confirmCode()}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text className="font-semibold text-white">학생 인증 완료</Text>}
        </Pressable>
      </> : null}
    </View>
  );
}
