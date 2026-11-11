import React, { useEffect, useRef } from "react";
import {
  Animated,
  Easing,
  Text,
  View,
} from "react-native";

type LoginLoadingOverlayProps = {
  visible: boolean;
  message?: string;
};

export function LoginLoadingOverlay({
  visible,
  message = "로그인 중입니다",
}: LoginLoadingOverlayProps) {
  const dots = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
  ]).current;

  useEffect(() => {
    if (!visible) return;

    const animations = dots.map((dot, index) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(index * 140),
          Animated.timing(dot, {
            toValue: 1,
            duration: 420,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 420,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.delay((2 - index) * 140),
        ]),
      ),
    );

    animations.forEach((animation) => animation.start());

    return () => {
      animations.forEach((animation) => animation.stop());
      dots.forEach((dot) => dot.setValue(0));
    };
  }, [dots, visible]);

  if (!visible) return null;

  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={message}
      className="absolute inset-0 z-50 items-center justify-center bg-black/35"
    >
      <View className="items-center rounded-2xl bg-white px-8 py-7 shadow-lg dark:bg-neutral-900">
        <View className="mb-4 flex-row items-center justify-center">
          {dots.map((dot, index) => (
            <Animated.View
              key={index}
              className="mx-1 h-2.5 w-2.5 rounded-full bg-[#0a7ea4]"
              style={{
                opacity: dot.interpolate({ inputRange: [0, 1], outputRange: [0.35, 1] }),
                transform: [
                  {
                    translateY: dot.interpolate({ inputRange: [0, 1], outputRange: [3, -3] }),
                  },
                ],
              }}
            />
          ))}
        </View>
        <Text className="text-sm font-medium text-neutral-800 dark:text-white">
          {message}...
        </Text>
        <Text className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          잠시만 기다려 주세요
        </Text>
      </View>
    </View>
  );
}
