import * as WebBrowser from 'expo-web-browser';
import { Link, router } from "expo-router";

import { hrefAppHome, hrefSignup } from "@/constants/routes";
import React, { useState, useCallback, useEffect } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage, logDevAxiosError } from "@/api/errors";
import { useAuthStore } from "@/features/auth/store/auth-store";

WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const ready = useAuthStore((s) => s.ready);
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [emailMessage, setEmailMessage] = useState<string>('')
  const [passwordMessage, setPasswordMessage] = useState<string>('')

  const [isEmail, setIsEmail] = useState<boolean>(false)
  const [isPassword, setIsPassword] = useState<boolean>(false)

  const onChangeEmail = useCallback((text: string) => {
    const emailRegEx = /^[A-Za-z0-9]([-_.]?[A-Za-z0-9])*@[A-Za-z0-9]([-_.]?[A-Za-z0-9])*\.[A-Za-z]{2,3}$/i
    setEmail(text)

    if (!emailRegEx.test(text)) {
      setEmailMessage('이메일 형식을 확인하세요')
      setIsEmail(false)
    } else {
      setEmailMessage('')
      setIsEmail(true)
    }
  }, [])

  const onChangePassword = useCallback((text: string) => {
    /*
    const passwordRegEx = /^(?=.*[a-zA-Z])(?=.*[!@#$%^*+=-])(?=.*[0-9]).{8,25}$/
    setPassword(text)

    if (!passwordRegEx.test(text)) {
      /*
      setPasswordMessage('비밀번호 형식을 확인하세요')
      setIsPassword(false)
    } else {
      setPasswordMessage('안전한 비밀번호입니다')
      setIsPassword(true)
      }
    */
   
    setPasswordMessage('올바른 형식입니다')
    setPassword(text)
    setPasswordMessage('')
    setIsPassword(true)
  }, [])
  
  useEffect(() => {
    if (ready && user) {
      router.replace(hrefAppHome);
    }
  }, [ready, user]);

  if (!ready || user) {
    return null;
  }

  async function onSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      router.replace(hrefAppHome);
    } catch (e) {
      logDevAxiosError("login", e);
      setError(getAxiosErrorMessage(e, "로그인에 실패했습니다."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white dark:bg-neutral-950"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}
    >
      <View className="flex-1 justify-center px-6">
        <Text className="text-2xl font-bold text-neutral-900 dark:text-white">로그인</Text>
        <Text className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          KNU Campus Life
        </Text>

        {error ? (
          <View className="mt-4 rounded-lg bg-red-100 p-3 dark:bg-red-900/40">
            <Text className="text-sm text-red-800 dark:text-red-200">{error}</Text>
          </View>
        ) : null}
        <View className="mt-6">
          <Text className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            이메일
          </Text>
          <TextInput
            className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            onChangeText={onChangeEmail}
            value={email}
          />
          {email.length > 0 && (
            <Text className={`mt-1 text-xs ${isEmail ? 'text-green-600' : 'text-red-500'}`}>
              {emailMessage}
            </Text>
          )}
        </View>

        <View className="mt-4">
          <Text className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            비밀번호 (숫자+영문자+특수문자 (8자리 이상))
          </Text>
          <TextInput
            className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            secureTextEntry
            autoComplete="password"
            onChangeText={onChangePassword}
            value={password}
          />
          {password.length > 0 && (
            <Text className={`mt-1 text-xs ${isPassword ? 'text-green-600' : 'text-red-500'}`}>
              {passwordMessage}
            </Text>
          )}
        </View>

        <Pressable
          className="mt-8 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
          disabled={submitting || !email.trim() || !password}
          onPress={() => void onSubmit()}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="font-semibold text-white">로그인</Text>
          )}
        </Pressable>

        <Link href={hrefSignup} asChild>
          <Pressable className="mt-6 items-center py-2">
            <Text className="text-[#0a7ea4] dark:text-sky-300">계정이 없으신가요? 회원가입</Text>
          </Pressable>
        </Link>
      </View>
    </KeyboardAvoidingView>
  );
}
