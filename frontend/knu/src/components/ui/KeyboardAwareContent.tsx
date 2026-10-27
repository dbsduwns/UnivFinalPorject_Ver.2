import { type PropsWithChildren, useCallback, useEffect, useRef, useState } from "react";
import { Keyboard, KeyboardAvoidingView, Platform, View } from "react-native";

import { APP_HEADER_HEIGHT } from "./HomeHeader";

export const KeyboardAwareContent = ({ children }: PropsWithChildren) => {
  const contentRef = useRef<View>(null);
  const keyboardTopRef = useRef<number | null>(null);
  const [keyboardOverlap, setKeyboardOverlap] = useState(0);

  const measureKeyboardOverlap = useCallback(() => {
    const keyboardTop = keyboardTopRef.current;
    if (keyboardTop === null) return;

    contentRef.current?.measureInWindow((_x, y, _width, height) => {
      if (keyboardTopRef.current !== keyboardTop) return;
      setKeyboardOverlap(Math.max(0, Math.ceil(y + height - keyboardTop)));
    });
  }, []);

  useEffect(() => {
    if (Platform.OS !== "android") return;

    let frameId: number | null = null;
    const scheduleMeasurement = () => {
      if (frameId !== null) cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        frameId = null;
        measureKeyboardOverlap();
      });
    };

    const showSubscription = Keyboard.addListener("keyboardDidShow", (event) => {
      keyboardTopRef.current = event.endCoordinates.screenY;
      scheduleMeasurement();
    });
    const hideSubscription = Keyboard.addListener("keyboardDidHide", () => {
      keyboardTopRef.current = null;
      setKeyboardOverlap(0);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
      if (frameId !== null) cancelAnimationFrame(frameId);
    };
  }, [measureKeyboardOverlap]);

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? APP_HEADER_HEIGHT : 0}
    >
      <View
        ref={contentRef}
        collapsable={false}
        style={{ flex: 1, paddingBottom: Platform.OS === "android" ? keyboardOverlap : 0 }}
        onLayout={Platform.OS === "android" ? measureKeyboardOverlap : undefined}
      >
        {children}
      </View>
    </KeyboardAvoidingView>
  );
};
