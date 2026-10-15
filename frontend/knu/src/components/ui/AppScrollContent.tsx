import { forwardRef, type PropsWithChildren } from "react";
import type {
  NativeScrollEvent,
  NativeSyntheticEvent,
  StyleProp,
  ViewStyle,
} from "react-native";
import { ScrollView, useWindowDimensions, View } from "react-native";

const CONTENT_MAX_WIDTH = 720;


type AppScrollContentProps = PropsWithChildren<{
  contentContainerStyle?: StyleProp<ViewStyle>;
  onContentSizeChange?: (contentWidth: number, contentHeight: number) => void;
  onScroll?: (event: NativeSyntheticEvent<NativeScrollEvent>) => void;
  scrollEventThrottle?: number;
}>;

export const AppScrollContent = forwardRef<ScrollView, AppScrollContentProps>(({
  children,
  contentContainerStyle,
  onContentSizeChange,
  onScroll,
  scrollEventThrottle,
}, ref) => {
  const { width } = useWindowDimensions();
  const horizontalPadding = width >= 768 ? 32 : 20;

  return (
    <ScrollView
      ref={ref}
      className="flex-1"
      keyboardDismissMode="none"
      keyboardShouldPersistTaps="always"
      scrollEnabled
      onContentSizeChange={onContentSizeChange}
      onScroll={onScroll}
      scrollEventThrottle={scrollEventThrottle}
      contentContainerStyle={[
        {
          paddingHorizontal: horizontalPadding,
          paddingVertical: 20,
          paddingBottom: 32,
        },
        contentContainerStyle,
      ]}
    >
      <View
        style={{
          width: "100%",
          maxWidth: CONTENT_MAX_WIDTH,
          alignSelf: "center",
          gap: 16,
        }}
      >
        {children}
      </View>
    </ScrollView>
  );
});

AppScrollContent.displayName = "AppScrollContent";
