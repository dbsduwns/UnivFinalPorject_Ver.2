import { Link, Redirect, router } from "expo-router";

import { hrefAppHome, hrefLogin } from "@/constants/routes";
import { useState } from "react";
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

export default function SignupScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const ready = useAuthStore((s) => s.ready);
  const signup = useAuthStore((s) => s.signup);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [student_id, setStudent_id] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!ready) {
    return null;
  }

  if (user) {
    return <Redirect href={hrefAppHome} />;
  }

  async function onSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        student_id,
      });
      router.replace(hrefAppHome);
    } catch (e) {
      logDevAxiosError("signup", e);
      setError(getAxiosErrorMessage(e, "회원가입에 실패했습니다."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
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
        <Text className="text-2xl font-bold text-neutral-900 dark:text-white">회원가입</Text>
        <Text className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          이메일로 간편하게 시작하세요
        </Text>

        {error ? (
          <View className="mt-4 rounded-lg bg-red-100 p-3 dark:bg-red-900/40">
            <Text className="text-sm text-red-800 dark:text-red-200">{error}</Text>
          </View>
        ) : null}
        <Text className="mt-6 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          이름
        </Text>
        <TextInput
          className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
          autoComplete="name"
          onChangeText={setName}
          value={name}
        />
        <Text className="mt-6 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          학번
        </Text>
        <TextInput
          className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
          autoComplete="name"
          onChangeText={setStudent_id}
          value={student_id}
        />
        <Text className="mt-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          이메일
        </Text>
        <TextInput
          className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={setEmail}
          value={email}
        />
        <Text className="mt-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          비밀번호
        </Text>
        <TextInput
          className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
          secureTextEntry
          autoComplete="new-password"
          onChangeText={setPassword}
          value={password}
        />
        <Pressable
          className="mt-8 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
          disabled={submitting || !name.trim() || !email.trim() || !password || !student_id}
          onPress={() => void onSubmit()}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="font-semibold text-white">가입 후 시작</Text>
          )}
        </Pressable>

        <Link href={hrefLogin} asChild>
          <Pressable className="mt-6 items-center py-2">
            <Text className="text-[#0a7ea4] dark:text-sky-300">이미 계정이 있어요</Text>
          </Pressable>
        </Link>
          </View>
        </ScrollView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}
