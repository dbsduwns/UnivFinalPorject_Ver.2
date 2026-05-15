import { Pressable, Text, View, ScrollView, TextInput } from "react-native";
import { Menu, Bell } from "lucide-react-native";

export const HomeHeader = () => {
    return (
        // Header ( Drawer / Title / Notifications )
        <View 
            className="Header justify-center items-center bg-[#1aaedb]"
            style={{ flex: 2 }}>
        {/* Drawer */}
        <View 
            className="MenuWrapper"
            style={{ position:"absolute", top: 40, left: 10 }}>
            <Menu 
                size={ 32 } color={'white'}
                style={{ position: 'absolute', top: 10, left: 10 }}/>
        </View>
        {/* Title */}
        <View 
            className="TitleWrapper justify-center items-center"
            style={{ marginTop: 10 }}>
            <Text style={{ fontSize: 30, fontWeight: 'bold', color: 'white'}}>강남대학교</Text>
            <Text style={{ fontSize: 12, fontWeight: 'bold', color: 'white' }}>KANGNAM UNIVERSITY</Text>
        </View>
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