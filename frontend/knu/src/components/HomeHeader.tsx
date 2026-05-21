import { Pressable, Text, View } from "react-native";
import { Menu, Bell } from "lucide-react-native";

import { useAppDrawer } from "@/components/AppDrawer";
import { router } from "expo-router";

export const HomeHeader = () => {
    const { toggleDrawer } = useAppDrawer();

    const HomeHref = "/(app)/(tabs)";

    return (
        // Header ( Drawer / Title / Notifications )
        <View 
            className="Header justify-center items-center bg-[#1aaedb]"
            style={{ height: 110 }}>
            {/* Drawer */}
            <Pressable
                onPress={toggleDrawer}
                className="MenuWrapper"
                style={{ position:"absolute", top: 40, left: 10, width: 52, height: 52 }}>
                <Menu size={ 32 } color={'white'} style={{ position: 'absolute', top: 10, left: 10 }}/>
            </Pressable>
            {/* Title */}
            <Pressable
                className="TitleWrapper justify-center items-center"
                style={{ marginTop: 10 }}
                key={HomeHref}
                onPress={() => router.push(HomeHref)}>
                <Text style={{ fontSize: 30, fontWeight: 'bold', color: 'white'}}>강남대학교</Text>
                <Text style={{ fontSize: 12, fontWeight: 'bold', color: 'white' }}>KANGNAM UNIVERSITY</Text>
            </Pressable>
            {/* Notification */}
            <View 
                className="NotificationWrapper"
                style={{ position:"absolute", top: 40, right: 10 }}>
                <Bell 
                    size={ 32 } color={ 'white' }
                    style={{ position: 'absolute', top: 10, right: 10 }} />
            </View>
        </View>
    )
}
