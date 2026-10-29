import { Link, router, useLocalSearchParams } from "expo-router";

import { hrefAppHome, hrefSignup } from "@/constants/routes";
import React, { useState, useCallback, useEffect } from "react";
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


export default function ResetPassword() {

    const insets = useSafeAreaInsets();    
    
    const [email, setEmail] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [emailMessage, setEmailMessage] = useState<string>('')

    
    const [isEmail, setIsEmail] = useState<boolean>(false)

    
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

    
    async function onSubmit() {
    setError(null);
    setSubmitting(true);
    try {

    } catch (e) {
      
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
    
                <Pressable
                  className="mt-8 items-center rounded-lg bg-[#0a7ea4] py-3 active:opacity-90 disabled:opacity-50"
                  disabled={submitting || !email.trim()}
                  onPress={() => void onSubmit()}
                >
                  {submitting ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text className="font-semibold text-white">비밀번호 찾기</Text>
                  )}
                </Pressable>
              </View>
            </ScrollView>
          </TouchableWithoutFeedback>
        </KeyboardAvoidingView>
    );
}