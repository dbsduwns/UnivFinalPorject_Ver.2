import { Pressable, Text, View } from "react-native";
import { Menu } from "lucide-react-native";

import { useAppDrawer } from "@/components/ui/AppDrawer";
import { router } from "expo-router";
import { ChatIconWithBadge } from "@/features/chat/components/ChatIconWithBadge";
import { useUnreadChatCount } from "@/features/chat/hooks/useUnreadChatCount";
import { NotificationCenterButton } from "@/features/notifications/components/NotificationCenter";

export const APP_HEADER_HEIGHT = 90;

export const HomeHeader = () => {
    const { toggleDrawer } = useAppDrawer();
    const unreadChatCount = useUnreadChatCount();

    const HomeHref = "/(app)/(tabs)";

    return (
        // Header ( Drawer / Title / Talk / Notifications )
        <View 
            className="Header flex-row items-center"
            style={{ 
                height: APP_HEADER_HEIGHT,
                paddingTop: 20,
                paddingHorizontal: 10,
                backgroundColor: "#FFFFFF",
            }}>
            {/* Drawer */}
            <Pressable
                onPress={toggleDrawer}
                className="MenuWrapper"
                style={{ 
                    width: 52,
                    height: 52,
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                <Menu size={ 32 } color={'#13708D'} />
            </Pressable>
            {/* Title */}
            <Pressable
                className="TitleWrapper items-left"
                style={{ marginLeft: 4}}
                key={HomeHref}
                onPress={() => router.push(HomeHref)}>
                <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#111827'}}>KNU Campus</Text>
                <Text style={{ fontSize: 12, fontWeight: 'bold', color: '#6B7280' }}>강남대학교</Text>
            </Pressable>
            <View 
                className="NotificationWrapper flex-row"
                style={{
                    marginLeft: "auto",
                    alignItems: "center",
                    justifyContent: "center",
                 }}>
                {/* Talk  */}
                <Pressable
                    onPress={() => router.push("/(app)/(tabs)/messages")}
                    accessibilityRole="button"
                    accessibilityLabel={unreadChatCount > 0 ? `쪽지 열기, 읽지 않은 메시지 ${unreadChatCount}개` : "쪽지 열기"}
                    className="items-center justify-center"
                    style={{ 
                        width: 45,
                        height: 45,
                        borderRadius: 32,
                        marginRight: 10,
                        backgroundColor: "#EAF8FC"}}>
                    <ChatIconWithBadge size={26} color="#13708D" strokeWidth={2.5} unreadCount={unreadChatCount} />
                </Pressable>
                <NotificationCenterButton />
            </View>
        </View>
    )
}
