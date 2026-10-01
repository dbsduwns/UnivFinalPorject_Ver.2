import { Pressable, Text, View } from "react-native";
import { Menu, Bell, MessageCircle } from "lucide-react-native";

import { useAppDrawer } from "@/components/ui/AppDrawer";
import { router } from "expo-router";

export const HomeHeader = () => {
    const { toggleDrawer } = useAppDrawer();

    const HomeHref = "/(app)/(tabs)";

    return (
        // Header ( Drawer / Title / Talk / Notifications )
        <View 
            className="Header flex-row items-center"
            style={{ 
                height: 90,
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
                    onPress={() => router.push("/(app)/messages")}
                    accessibilityRole="button"
                    accessibilityLabel="쪽지 열기"
                    className="items-center justify-center"
                    style={{ 
                        width: 45,
                        height: 45,
                        borderRadius: 32,
                        marginRight: 10,
                        backgroundColor: "#EAF8FC"}}>
                    <MessageCircle  
                    size={ 26 } color={ '#13708D' } strokeWidth={2.5}
                    />
                </Pressable>
                {/* Notification */}
                <Bell size={ 32 } color={ '#6B7280' } />
            </View>
        </View>
    )
}
