import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { getAxiosErrorMessage, logDevAxiosError } from "@/api/errors";
import {
  confirmStudentVerification,
  requestStudentVerification,
} from "@/features/auth/api/auth";
import { useAuthStore } from "@/features/auth/store/auth-store";
import * as onboardingStorage from "@/features/auth/services/onboarding-storage";


export default function StudentVerificationScreen() {
  const { onboardingToken } = useLocalSearchParams<{ onboardingToken?: string }>();
  const completeGoogleLogin = useAuthStore((state) => state.completeGoogleLogin);
  const clearPendingOnboarding = useAuthStore((state) => state.clearPendingOnboarding);

  const [activeOnboardingToken, setActiveOnboardingToken] = useState(onboardingToken ?? "");
  const [studentEmail, setStudentEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationId, setVerificationId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeOnboardingToken) return;

    void onboardingStorage.getPendingOnboarding().then((pending) => {
      if (pending) {
        setActiveOnboardingToken(pending.onboardingToken);
      } else {
        setError("학생 인증 세션이 만료되었습니다. Google 로그인을 다시 진행해 주세요.");
      }
    });
  }, [activeOnboardingToken]);

  async function requestCode() {
    if (!activeOnboardingToken) {
      setError("Google 가입 세션이 없습니다. 다시 로그인해 주세요.");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const result = await requestStudentVerification({
        onboarding_token: activeOnboardingToken,
        student_email: studentEmail.trim(),
      });
      setVerificationId(result.verification_id);
      Alert.alert("인증 코드 발송", "강남대학교 이메일의 받은편지함을 확인해 주세요.");
    } catch (e) {
      logDevAxiosError("student-verification-request", e);
      setError(getAxiosErrorMessage(e, "인증 코드 발송에 실패했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function confirmCode() {
    if (!activeOnboardingToken || verificationId === null) {
      setError("먼저 인증 코드를 요청해 주세요.");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const tokens = await confirmStudentVerification({
        verification_id: verificationId,
        onboarding_token: activeOnboardingToken,
        otp: otp.trim(),
      });
      await completeGoogleLogin(tokens);
      router.replace("/(app)/(tabs)");
    } catch (e) {
      logDevAxiosError("student-verification-confirm", e);
      setError(getAxiosErrorMessage(e, "학생 인증에 실패했습니다."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="flex-1 bg-white px-6 pt-24 dark:bg-neutral-950">
      <Text className="text-2xl font-bold text-neutral-900 dark:text-white">
        학생 인증
      </Text>
      <Text className="mt-2 text-sm leading-5 text-neutral-500 dark:text-neutral-400">
        Google 로그인 후 강남대학교 이메일 인증을 완료해야 가입이 완료됩니다.
      </Text>

      {error ? (
        <View className="mt-5 rounded-lg bg-red-100 p-3 dark:bg-red-900/40">
          <Text className="text-sm text-red-800 dark:text-red-200">{error}</Text>
        </View>
      ) : null}

      <Text className="mt-8 text-sm font-medium text-neutral-700 dark:text-neutral-300">
        강남대학교 이메일
      </Text>
      <TextInput
        className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        onChangeText={setStudentEmail}
        placeholder="학번@kangnam.ac.kr"
        value={studentEmail}
      />

      <Pressable
        className="mt-4 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
        disabled={loading || !studentEmail.trim()}
        onPress={() => void requestCode()}
      >
        {loading && verificationId === null ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text className="font-semibold text-white">인증 코드 받기</Text>
        )}
      </Pressable>

      {verificationId !== null ? (
        <>
          <Text className="mt-6 text-sm font-medium text-neutral-700 dark:text-neutral-300">
            인증 코드
          </Text>
          <TextInput
            className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base tracking-[6px] text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            keyboardType="number-pad"
            maxLength={6}
            onChangeText={setOtp}
            placeholder="123456"
            value={otp}
          />
          <Pressable
            className="mt-4 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
            disabled={loading || otp.length !== 6}
            onPress={() => void confirmCode()}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="font-semibold text-white">학생 인증 완료</Text>
            )}
          </Pressable>
        </>
      ) : null}

      <Pressable
        className="mt-6 items-center py-2"
        disabled={loading}
        onPress={() => {
          void clearPendingOnboarding();
          router.replace("/(auth)/login");
        }}
      >
        <Text className="text-sm text-neutral-500 dark:text-neutral-400">
          나중에 인증하기
        </Text>
      </Pressable>
    </View>
  );
}
