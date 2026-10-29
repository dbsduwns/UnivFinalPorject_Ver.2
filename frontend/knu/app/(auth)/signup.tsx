import { Link, Redirect, router, useLocalSearchParams } from "expo-router";
import { isAxiosError } from "axios";

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

type SignupField = "name" | "studentId" | "email" | "password";
type SignupFieldErrors = Partial<Record<SignupField, string>>;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PASSWORD_PATTERN = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S{8,}$/;

function getFieldError(field: SignupField, value: string): string | undefined {
  const trimmedValue = value.trim();

  switch (field) {
    case "name":
      if (!trimmedValue) return "이름을 입력해 주세요.";
      if (trimmedValue.length < 2) return "이름은 두 글자 이상 입력해 주세요.";
      if (trimmedValue.length > 50) return "이름은 50자 이내로 입력해 주세요.";
      return undefined;
    case "studentId":
      if (!trimmedValue) return "학번을 입력해 주세요.";
      if (trimmedValue.length < 4 || trimmedValue.length > 20) return "학번은 4~20자로 입력해 주세요.";
      return undefined;
    case "email":
      if (!trimmedValue) return "이메일을 입력해 주세요.";
      if (!EMAIL_PATTERN.test(trimmedValue)) return "예: example@kangnam.ac.kr 형식으로 입력해 주세요.";
      return undefined;
    case "password":
      if (!value) return "비밀번호를 입력해 주세요.";
      if (!PASSWORD_PATTERN.test(value)) return "영문, 숫자, 특수문자를 각각 포함해 8자 이상 입력해 주세요.";
      if (value.length > 72) return "비밀번호는 72자 이내로 입력해 주세요.";
      return undefined;
  }
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <Text className="mt-1.5 text-xs leading-5 text-red-600 dark:text-red-300">{message}</Text>;
}

function getServerFieldErrors(error: unknown): SignupFieldErrors {
  if (!isAxiosError(error)) return {};

  const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") {
    if (detail.includes("이메일")) return { email: "이미 사용 중인 이메일입니다. 다른 이메일을 입력해 주세요." };
    if (detail.includes("학번")) return { studentId: "이미 등록된 학번입니다. 입력한 학번을 확인해 주세요." };
    return {};
  }

  if (!Array.isArray(detail)) return {};
  return detail.reduce<SignupFieldErrors>((errors, item) => {
    if (typeof item !== "object" || item === null) return errors;
    const location = (item as { loc?: unknown }).loc;
    const field = Array.isArray(location) ? location.at(-1) : undefined;
    if (field === "name") errors.name = "이름은 2~50자로 입력해 주세요.";
    if (field === "student_id") errors.studentId = "학번은 4~20자로 입력해 주세요.";
    if (field === "email") errors.email = "올바른 이메일 형식을 입력해 주세요.";
    if (field === "password") errors.password = "비밀번호 형식을 다시 확인해 주세요.";
    return errors;
  }, {});
}

export default function SignupScreen() {
  const { redirect } = useLocalSearchParams<{ redirect?: string }>();
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const ready = useAuthStore((s) => s.ready);
  const signup = useAuthStore((s) => s.signup);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [studentId, setStudentId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<SignupFieldErrors>({});

  // Preserve an invite destination through sign-up.  Only internal paths are
  // accepted so a crafted link cannot redirect a newly registered user away
  // from the app.
  const signupDestination =
    typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//")
      ? redirect
      : hrefAppHome;

  if (!ready) {
    return null;
  }

  if (user) {
    return <Redirect href={hrefAppHome} />;
  }

  async function onSubmit() {
    const errors: SignupFieldErrors = {
      name: getFieldError("name", name),
      studentId: getFieldError("studentId", studentId),
      email: getFieldError("email", email),
      password: getFieldError("password", password),
    };
    const validErrors = Object.fromEntries(
      Object.entries(errors).filter(([, message]) => message),
    ) as SignupFieldErrors;
    setFieldErrors(validErrors);
    if (Object.keys(validErrors).length > 0) return;

    setFormError(null);
    setSubmitting(true);
    try {
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        student_id: studentId.trim(),
      });
      router.replace(signupDestination as never);
    } catch (e) {
      logDevAxiosError("signup", e);
      const serverFieldErrors = getServerFieldErrors(e);
      if (Object.keys(serverFieldErrors).length > 0) {
        setFieldErrors((current) => ({ ...current, ...serverFieldErrors }));
      } else {
        setFormError(getAxiosErrorMessage(e, "회원가입에 실패했습니다."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  function updateField(field: SignupField, value: string) {
    if (field === "name") setName(value);
    if (field === "studentId") setStudentId(value);
    if (field === "email") setEmail(value);
    if (field === "password") setPassword(value);

    setFormError(null);
    setFieldErrors((current) => ({ ...current, [field]: getFieldError(field, value) }));
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

        {formError ? (
          <View className="mt-4 rounded-lg bg-red-100 p-3 dark:bg-red-900/40">
            <Text className="text-sm text-red-800 dark:text-red-200">{formError}</Text>
          </View>
        ) : null}
        <Text className="mt-6 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          이름
        </Text>
        <TextInput
          className={`mt-1 rounded-lg border bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:bg-neutral-900 dark:text-white ${fieldErrors.name ? "border-red-500 dark:border-red-400" : "border-neutral-200 dark:border-neutral-700"}`}
          autoComplete="name"
          onChangeText={(value) => updateField("name", value)}
          value={name}
        />
        <FieldError message={fieldErrors.name} />
        <Text className="mt-6 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          학번
        </Text>
        <TextInput
          className={`mt-1 rounded-lg border bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:bg-neutral-900 dark:text-white ${fieldErrors.studentId ? "border-red-500 dark:border-red-400" : "border-neutral-200 dark:border-neutral-700"}`}
          autoComplete="name"
          keyboardType="number-pad"
          onChangeText={(value) => updateField("studentId", value)}
          value={studentId}
        />
        <FieldError message={fieldErrors.studentId} />
        <Text className="mt-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          이메일
        </Text>
        <TextInput
          className={`mt-1 rounded-lg border bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:bg-neutral-900 dark:text-white ${fieldErrors.email ? "border-red-500 dark:border-red-400" : "border-neutral-200 dark:border-neutral-700"}`}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={(value) => updateField("email", value)}
          value={email}
        />
        <FieldError message={fieldErrors.email} />
        <Text className="mt-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">
          비밀번호
        </Text>
        <TextInput
          className={`mt-1 rounded-lg border bg-neutral-50 px-3 py-3 text-base text-neutral-900 dark:bg-neutral-900 dark:text-white ${fieldErrors.password ? "border-red-500 dark:border-red-400" : "border-neutral-200 dark:border-neutral-700"}`}
          secureTextEntry
          autoComplete="new-password"
          onChangeText={(value) => updateField("password", value)}
          value={password}
        />
        <FieldError message={fieldErrors.password} />
        <Pressable
          className="mt-8 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
          disabled={submitting || !name.trim() || !email.trim() || !password || !studentId}
          onPress={() => void onSubmit()}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="font-semibold text-white">가입 후 시작</Text>
          )}
        </Pressable>

            <Link
              href={
                signupDestination === hrefAppHome
                  ? hrefLogin
                  : { pathname: "/(auth)/login", params: { redirect: signupDestination } }
              }
              asChild
            >
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
