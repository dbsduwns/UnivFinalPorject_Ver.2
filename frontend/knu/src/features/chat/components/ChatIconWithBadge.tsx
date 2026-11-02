import { View } from "react-native";
import { MessageCircle } from "lucide-react-native";
import { UnreadCountBadge } from "./UnreadCountBadge";

type ChatIconWithBadgeProps = {
  size: number;
  color: string;
  unreadCount: number;
  strokeWidth?: number;
};

export function ChatIconWithBadge({ size, color, unreadCount, strokeWidth }: ChatIconWithBadgeProps) {
  return (
    <View style={{ width: size, height: size, position: "relative" }}>
      <MessageCircle size={size} color={color} strokeWidth={strokeWidth} />
      <UnreadCountBadge count={unreadCount} style={{ position: "absolute", top: -7, right: -11 }} />
    </View>
  );
}
