import React, { useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableWithoutFeedback,
  View,
} from "react-native";
import { Link } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import { hrefLogin } from "@/constants/routes";
import { requestPasswordReset } from "@/features/auth/api/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ResetPasswordScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const validEmail = EMAIL_PATTERN.test(email.trim());

  async function onSubmit() {
    if (!validEmail || submitting) return;

    setError(null);
    setSent(false);
    setSubmitting(true);
    try {
      await requestPasswordReset({ email: email.trim() });
      setSent(true);
    } catch (e) {
      setError(getAxiosErrorMessage(e, "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white dark:bg-neutral-950"
      behavior="padding"
      keyboardVerticalOffset={Platform.OS === "ios" ? insets.top : 0}
    >
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: "center",
            paddingTop: insets.top,
            paddingBottom: insets.bottom > 0 ? insets.bottom : 24,
          }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View className="px-6">
            <Text className="text-2xl font-bold text-neutral-900 dark:text-white">비밀번호 찾기</Text>
            <Text className="mt-2 text-sm leading-5 text-neutral-500 dark:text-neutral-400">
              가입한 이메일 주소를 입력하면 비밀번호 재설정 안내를 보내드립니다.
            </Text>

            {error ? (
              <View className="mt-4 rounded-lg bg-red-100 p-3 dark:bg-red-900/40">
                <Text className="text-sm text-red-800 dark:text-red-200">{error}</Text>
              </View>
            ) : null}

            {sent ? (
              <View className="mt-4 rounded-lg bg-green-100 p-3 dark:bg-green-900/40">
                <Text className="text-sm leading-5 text-green-800 dark:text-green-200">
                  입력한 이메일이 등록되어 있다면 재설정 안내를 발송했습니다. 받은편지함과 스팸함을 확인해 주세요.
                </Text>
              </View>
            ) : null}

            <View className="mt-6">
              <Text className="text-sm font-medium text-neutral-700 dark:text-neutral-300">이메일</Text>
              <TextInput
                className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                returnKeyType="send"
                onSubmitEditing={() => void onSubmit()}
                onChangeText={(value) => {
                  setEmail(value);
                  setSent(false);
                  setError(null);
                }}
                value={email}
              />
              {email.length > 0 && !validEmail ? (
                <Text className="mt-1 text-xs text-red-500">이메일 형식을 확인하세요.</Text>
              ) : null}
            </View>

            <Pressable
              className="mt-8 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
              disabled={submitting || !validEmail}
              onPress={() => void onSubmit()}
            >
              {submitting ? <ActivityIndicator color="#fff" /> : (
                <Text className="font-semibold text-white">재설정 이메일 보내기</Text>
              )}
            </Pressable>

            <Link href={hrefLogin} asChild>
              <Pressable className="mt-4 items-center py-2">
                <Text className="text-[#0a7ea4] dark:text-sky-300">로그인으로 돌아가기</Text>
              </Pressable>
            </Link>
          </View>
        </ScrollView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}
