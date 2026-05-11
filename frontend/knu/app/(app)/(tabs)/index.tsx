import { router } from "expo-router";
import { Pressable, Text, View, ScrollView, TextInput } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { googleLoginRequest } from "@/features/auth/api/auth";
import { Bold, Radius } from "lucide-react-native";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <View className="Home flex-1 flex-col bg-white">
      <View 
        className="Header justify-center itmes-center bg-[#1aaedb]"
        style={{ flex: 2 }}>
        <View 
          className="MenuWrapper"
          style={{ position:"absolute", top: 40, left: 10 }}>
          <Ionicons name="menu" size={32} color={'white'}></Ionicons>
        </View>
        <View 
          className="TitleWrapper justify-center items-center"
          style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 30, fontWeight: 'bold', color: 'white'}}>강남대학교</Text>
          <Text style={{ fontSize: 12, fontWeight: 'bold', color: 'white' }}>KANGNAM UNIVERSITY</Text>
        </View>
        <View 
          className="NotificationWrapper"
          style={{ position:"absolute", top: 40, right: 10 }}>
          <Ionicons name="notifications-outline" size={32} color={'white'}></Ionicons>
        </View>
      </View>
      <View className="Contents" style={{ flex: 12 }}>
        <ScrollView 
        className="Scroll flex-1 "
        contentContainerClassName="justify-center items-center">
          <View 
          className="ChatWrapper flex-row mx-5 mt-5"
          style={{ 
            justifyContent: "center",
            alignItems: 'center',
            borderWidth: 1,
            borderColor: 'gray',
            borderRadius: 15
          }}>
            <View className="TextinputWrapper" style={{ flex: 9 }}>
              <TextInput 
              className="px-4"
              placeholder="무엇이든 물어보세요 ..."
              />
            </View>
            <View className="MicWrapper" style={{ flexDirection: "row" }}>
              <Ionicons name="mic" size={20} color={"#1aaedb"}></Ionicons>
            </View>
          </View>
          <View className="FaqWrapper flex-row w-full px-5 mt-4" 
            style={{ justifyContent: 'flex-start', alignItems: 'center' }}>
            <View style={{ borderWidth:1, borderRadius: 20, borderColor: 'gray', marginRight: 10}}>
              <Text className="p-2" style={{ fontSize: 12 }}>오늘 시간표</Text>
            </View>
            <View style={{ borderWidth:1, borderRadius: 20, borderColor: 'gray', marginRight: 10}}>
              <Text className="p-2" style={{ fontSize: 12 }}>중간고사 기간 알려줘</Text>
            </View>
          </View>
        </ScrollView>
      </View>
    </View>
  );
}