import * as WebBrowser from 'expo-web-browser';
import * as Google from "expo-auth-session/providers/google";
import { Link, router, useLocalSearchParams } from "expo-router";

import { hrefAppHome, hrefSignup } from "@/constants/routes";
import React, { useState, useCallback, useEffect, useRef } from "react";
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
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage, logDevAxiosError } from "@/api/errors";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { API_BASE_URL } from '@/constants/config';
import { LoginLoadingOverlay } from "@/components/LoginLoadingOverlay";

WebBrowser.maybeCompleteAuthSession();


export default function LoginScreen() {
  const { redirect } = useLocalSearchParams<{ redirect?: string }>();
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const ready = useAuthStore((s) => s.ready);
  const login = useAuthStore((s) => s.login);
  const googleLogin = useAuthStore((s) => s.googleLogin);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [emailMessage, setEmailMessage] = useState<string>('')
  const [passwordMessage, setPasswordMessage] = useState<string>('')

  const [isEmail, setIsEmail] = useState<boolean>(false)
  const [isPassword, setIsPassword] = useState<boolean>(false)
  const showLoginSuccessRef = useRef(false);

  // On Android/iOS, use the authorization-code flow. Expo exchanges the code
  // and exposes the resulting ID token in `authentication.idToken`.
  const [googleRequest, googleResponse, promptGoogleAsync] = Google.useIdTokenAuthRequest({
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    scopes: ["openid", "profile", "email"],
  });

  const loginDestination =
    typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//")
      ? redirect
      : hrefAppHome;


  useEffect(() => {
    console.log("EXPO_PUBLIC_API_URL");
    console.log(process.env.EXPO_PUBLIC_API_URL);

    console.log("API_BASE_URL");
    console.log(API_BASE_URL);
  }, []);

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
    setPassword(text)

    // 영문, 숫자, 특수문자를 각각 하나 이상 포함하고 공백 없이 8자 이상이어야 한다.
    const passwordRegEx = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S{8,}$/
    if (!passwordRegEx.test(text)) {
      setPasswordMessage('영문, 숫자, 특수문자를 포함해 8자 이상 입력하세요.')
      setIsPassword(false)
    } else {
      setPasswordMessage('')
      setIsPassword(true)
    }
  }, [])

  useEffect(() => {
    if (!ready || !user) return;

    if (showLoginSuccessRef.current) {
      router.replace({
        pathname: "/(auth)/login-success" as never,
        params: { redirect: loginDestination },
      });
      return;
    }

    if (ready && user) {
      router.replace(loginDestination as never);
    }
  }, [ready, user, loginDestination]);

  useEffect(() => {
    if (googleResponse) {
      console.warn("[GoogleLogin] AuthSession response:", googleResponse.type);
    }
    if (googleResponse?.type === "error") {
      setError("Google 로그인 요청이 취소되었거나 실패했습니다.");
      return;
    }
    if (googleResponse?.type !== "success") return;

    const idToken =
      googleResponse.authentication?.idToken ??
      googleResponse.params?.id_token;
    if (!idToken) {
      setError("Google ID token을 받지 못했습니다.");
      return;
    }

    void (async () => {
      setError(null);
      setGoogleSubmitting(true);
      showLoginSuccessRef.current = true;
      try {
        const result = await googleLogin(idToken);

        if (result.status === "student_verification_required") {
          router.push({
            pathname: "/student-verification" as never,
            params: { onboardingToken: result.onboarding_token },
          });
        } else if (result.status === "link_required") {
          setError(result.message);
        }
      } catch (e) {
        logDevAxiosError("google-login", e);
        setError(getAxiosErrorMessage(e, "Google 로그인에 실패했습니다."));
      } finally {
        setGoogleSubmitting(false);
      }
    })();
  }, [googleResponse, googleLogin, loginDestination]);

  if (!ready || user) {
    return null;
  }

  async function onSubmit() {
    if (!isPassword) {
      setPasswordMessage('영문, 숫자, 특수문자를 포함해 8자 이상 입력하세요.');
      return;
    }

    setError(null);
    setSubmitting(true);
    showLoginSuccessRef.current = true;
    try {
      await login({ email: email.trim(), password });
    } catch (e) {
      logDevAxiosError("login", e);
        setError(getAxiosErrorMessage(e, "로그인에 실패했습니다."));
        console.log("LOGIN ERROR", e);
        logDevAxiosError("login", e);
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <View className="flex-1">
      <KeyboardAvoidingView
        className="flex-1 bg-white dark:bg-neutral-950"
        behavior={Platform.OS === "ios" ? "padding" : "padding"}
        keyboardVerticalOffset={0}
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
              disabled={submitting || !email.trim() || !password || !isPassword}
              onPress={() => void onSubmit()}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text className="font-semibold text-white">로그인</Text>
              )}
            </Pressable>

            <View className="my-5 flex-row items-center">
              <View className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
              <Text className="mx-3 text-xs text-neutral-400">또는</Text>
              <View className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
            </View>

            <Pressable
              className="items-center rounded-lg border border-neutral-300 bg-white py-3 active:opacity-90 disabled:opacity-50 dark:border-neutral-600 dark:bg-neutral-900"
              disabled={!googleRequest || submitting || googleSubmitting}
              onPress={() => {
                console.warn("[GoogleLogin] button pressed");
                void promptGoogleAsync();
              }}
            >
              {googleSubmitting ? (
                <ActivityIndicator color="#111827" />
              ) : (
                <Text className="font-semibold text-neutral-800 dark:text-white">
                  Google로 로그인
                </Text>
              )}
            </Pressable>

            <Link href="/(auth)/reset-password" asChild>
              <Pressable className="mt-3 items-center py-2">
                <Text className="text-sm text-neutral-500 dark:text-neutral-400">비밀번호를 잊으셨나요?</Text>
              </Pressable>
            </Link>

            <Link href={hrefSignup} asChild>
              <Pressable className="mt-6 items-center py-2">
                <Text className="text-[#0a7ea4] dark:text-sky-300">계정이 없으신가요? 회원가입</Text>
              </Pressable>
            </Link>
          </View>
        </ScrollView>
      </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
      <LoginLoadingOverlay
        visible={submitting || googleSubmitting}
        message={googleSubmitting ? "Google 로그인 중입니다" : "로그인 중입니다"}
      />
    </View>
  );
}
