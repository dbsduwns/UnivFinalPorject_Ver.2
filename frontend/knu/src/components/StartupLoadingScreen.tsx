import React, { useEffect, useRef } from "react";
import { Animated, Easing, Text, View } from "react-native";

export function StartupLoadingScreen() {
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    animation.start();
    return () => animation.stop();
  }, [pulse]);

  return (
    <View className="flex-1 items-center justify-center bg-[#0a7ea4]">
      <Animated.View
        className="h-24 w-24 items-center justify-center rounded-[28px] bg-white shadow-lg"
        style={{
          opacity: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.88, 1] }),
          transform: [
            {
              scale: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.96, 1] }),
            },
          ],
        }}
      >
        <Text className="text-3xl font-extrabold text-[#0a7ea4]">KNU</Text>
      </Animated.View>

      <Text className="mt-6 text-xl font-bold text-white">KNU Campus Life</Text>
      <Text className="mt-2 text-sm text-white/75">앱을 준비하고 있습니다</Text>

      <View className="mt-8 flex-row items-center">
        {[0, 1, 2].map((index) => (
          <Animated.View
            key={index}
            className="mx-1 h-2 w-2 rounded-full bg-white"
            style={{
              opacity: pulse.interpolate({
                inputRange: [0, 0.5, 1],
                outputRange: index === 1 ? [0.4, 1, 0.4] : [0.25, 0.65, 0.25],
              }),
            }}
          />
        ))}
      </View>
    </View>
  );
}
