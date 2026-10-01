import type { PropsWithChildren } from "react";
import type { StyleProp, ViewStyle } from "react-native";
import { ScrollView, useWindowDimensions, View, Text } from "react-native";
import { useAuthStore } from "@/features/auth/store/auth-store";

const CONTENT_MAX_WIDTH = 720;


type AppScrollContentProps = PropsWithChildren<{
  contentContainerStyle?: StyleProp<ViewStyle>;
}>;

export const AppScrollContent = ({
  children,
  contentContainerStyle,
}: AppScrollContentProps) => {
  const { width } = useWindowDimensions();
  const horizontalPadding = width >= 768 ? 32 : 20;
  const user = useAuthStore(s => s.user);

  return (
    <ScrollView
      className="flex-1"
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
};
