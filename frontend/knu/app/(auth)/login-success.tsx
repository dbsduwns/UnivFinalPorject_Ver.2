import * as LocalAuthentication from "expo-local-authentication";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { hrefAppHome } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";
import * as biometricStorage from "@/features/auth/services/biometric-storage";

export default function LoginSuccessScreen() {
  const { redirect } = useLocalSearchParams<{ redirect?: string }>();
  const user = useAuthStore((state) => state.user);
  const [checking, setChecking] = useState(true);
  const [available, setAvailable] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const destination =
    typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//")
      ? redirect
      : hrefAppHome;

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const [hasHardware, isEnrolled, alreadyEnabled] = await Promise.all([
        LocalAuthentication.hasHardwareAsync(),
        LocalAuthentication.isEnrolledAsync(),
        biometricStorage.isBiometricLoginEnabled(),
      ]);

      if (cancelled) return;
      setAvailable(hasHardware && isEnrolled);
      setEnabled(alreadyEnabled);
      setChecking(false);

      if (alreadyEnabled) router.replace(destination as never);
    })();

    return () => {
      cancelled = true;
    };
  }, [destination]);

  async function enableBiometricLogin() {
    setSubmitting(true);
    setMessage(null);

    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: "생체 인증 로그인을 설정합니다",
        cancelLabel: "취소",
        biometricsSecurityLevel: "weak",
        disableDeviceFallback: false,
      });

      if (!result.success) {
        setMessage("생체 인증이 완료되지 않았습니다. 나중에 다시 설정할 수 있습니다.");
        return;
      }

      await biometricStorage.setBiometricLoginEnabled(true);
      setEnabled(true);
      setMessage("생체 인증 로그인이 설정되었습니다.");
    } catch {
      setMessage("생체 인증 설정 중 문제가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!user || checking) {
    return (
      <View className="flex-1 items-center justify-center bg-white dark:bg-neutral-950">
        <ActivityIndicator color="#0a7ea4" />
      </View>
    );
  }

  return (
    <View className="flex-1 justify-center bg-white px-6 dark:bg-neutral-950">
      <View className="items-center">
        <View className="h-20 w-20 items-center justify-center rounded-full bg-[#e6f5f8]">
          <Text className="text-4xl">✓</Text>
        </View>
        <Text className="mt-6 text-2xl font-bold text-neutral-900 dark:text-white">
          로그인 완료
        </Text>
        <Text className="mt-2 text-center text-sm leading-6 text-neutral-500 dark:text-neutral-400">
          {available
            ? "다음부터 생체 인증으로 더 빠르게 로그인할 수 있습니다."
            : "생체 인증은 기기 설정 후 사용할 수 있습니다."}
        </Text>
      </View>

      {available && !enabled ? (
        <View className="mt-10 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 dark:border-neutral-800 dark:bg-neutral-900">
          <Text className="text-base font-semibold text-neutral-900 dark:text-white">
            생체 인증 로그인 사용
          </Text>
          <Text className="mt-2 text-sm leading-5 text-neutral-500 dark:text-neutral-400">
            지문 또는 얼굴 인증을 사용해 로그인할 수 있습니다. 생체 정보는 앱에 저장되지 않습니다.
          </Text>
          <Pressable
            className="mt-5 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
            disabled={submitting}
            onPress={() => void enableBiometricLogin()}
          >
            {submitting ? <ActivityIndicator color="#fff" /> : <Text className="font-semibold text-white">사용하기</Text>}
          </Pressable>
        </View>
      ) : null}

      {message ? <Text className="mt-4 text-center text-sm text-neutral-500 dark:text-neutral-400">{message}</Text> : null}

      <Pressable
        className="mt-8 items-center py-3"
        onPress={() => router.replace(destination as never)}
      >
        <Text className="font-semibold text-[#0a7ea4]">{enabled ? "홈으로 이동" : "나중에 설정하기"}</Text>
      </Pressable>
    </View>
  );
}

