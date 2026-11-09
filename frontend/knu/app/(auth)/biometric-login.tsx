import { router } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { hrefAppHome, hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";

export default function BiometricLoginScreen() {
  const ready = useAuthStore((state) => state.ready);
  const user = useAuthStore((state) => state.user);
  const biometricRequired = useAuthStore((state) => state.biometricRequired);
  const unlockWithBiometric = useAuthStore((state) => state.unlockWithBiometric);
  const attempted = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unlock = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      const success = await unlockWithBiometric();
      if (!success) setError("생체 인증이 취소되었거나 실패했습니다.");
    } catch {
      setError("생체 인증을 사용할 수 없습니다. 일반 로그인으로 진행해 주세요.");
    } finally {
      setSubmitting(false);
    }
  }, [unlockWithBiometric]);

  useEffect(() => {
    if (!ready || user || !biometricRequired || attempted.current) return;
    attempted.current = true;
    void unlock();
  }, [ready, user, biometricRequired, unlock]);

  useEffect(() => {
    if (user) {
      router.replace(hrefAppHome);
    }
  }, [user]);

  if (user) return null;

  return (
    <View className="flex-1 justify-center bg-white px-6 dark:bg-neutral-950">
      <View className="items-center">
        <View className="h-20 w-20 items-center justify-center rounded-full bg-[#e6f5f8]">
          <Text className="text-4xl">⌁</Text>
        </View>
        <Text className="mt-6 text-2xl font-bold text-neutral-900 dark:text-white">
          생체 인증 로그인
        </Text>
        <Text className="mt-2 text-center text-sm leading-6 text-neutral-500 dark:text-neutral-400">
          등록된 지문 또는 얼굴 인증으로 로그인하세요.
        </Text>
      </View>

      {submitting ? <ActivityIndicator className="mt-10" color="#0a7ea4" /> : null}
      {error ? <Text className="mt-6 text-center text-sm text-red-500">{error}</Text> : null}

      <Pressable
        className="mt-10 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
        disabled={submitting}
        onPress={() => void unlock()}
      >
        <Text className="font-semibold text-white">다시 인증하기</Text>
      </Pressable>

      <Pressable
        className="mt-4 items-center py-3"
        disabled={submitting}
        onPress={() => router.replace(hrefLogin)}
      >
        <Text className="font-semibold text-[#0a7ea4]">일반 로그인 사용</Text>
      </Pressable>
    </View>
  );
}
