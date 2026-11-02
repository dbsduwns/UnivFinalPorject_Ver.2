import type { StyleProp, ViewStyle } from "react-native";
import { Text, View } from "react-native";

type UnreadCountBadgeProps = {
  count: number;
  size?: "icon" | "room";
  style?: StyleProp<ViewStyle>;
};

export function UnreadCountBadge({ count, size = "icon", style }: UnreadCountBadgeProps) {
  if (count <= 0) return null;

  const isRoom = size === "room";
  return (
    <View
      pointerEvents="none"
      accessibilityLabel={`읽지 않은 메시지 ${count}개`}
      style={[
        {
          minWidth: isRoom ? 28 : 17,
          height: isRoom ? 28 : 17,
          paddingHorizontal: isRoom ? 7 : 3,
          borderRadius: isRoom ? 14 : 9,
          borderWidth: 1.5,
          borderColor: "#FFFFFF",
          backgroundColor: "#F97316",
          alignItems: "center",
          justifyContent: "center",
        },
        style,
      ]}
    >
      <Text style={{ color: "#FFFFFF", fontSize: isRoom ? 13 : 9, fontWeight: "800", lineHeight: isRoom ? 17 : 12 }}>
        {count > 99 ? "99+" : count}
      </Text>
    </View>
  );
}
