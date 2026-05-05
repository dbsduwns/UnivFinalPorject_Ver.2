import { Tabs } from "expo-router";
import React from "react";
import { Home, Calendar, Bot, Bell, Compass, User } from "lucide-react-native";

import { HapticTab } from "@/components/haptic-tab";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? "light"].tint,
        headerShown: false,
        tabBarButton: HapticTab,
        tabBarStyle:{
          height: 100,
          paddingBottom: 10,
          paddingTop: 10,
          borderTopWidth: 0,
          elevation: 5,
          shadowOpacity: 0.1,
        }
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "홈",
          tabBarIcon: ({ color }) => (
            <Home size={28} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="schedule"
        options={{
          title: "시간표",
          tabBarIcon: ({ color }) => (
            <Calendar size={28} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="ai_chat"
        options={{
          title: "챗봇",
          tabBarIcon: ({ color }) => (
            <Bot size={40} color={color} style={{marginBottom:20}} />
          ),
        }}
      />
      <Tabs.Screen
        name="notice"
        options={{
          title: "공지",
          tabBarIcon: ({ color }) => (
            <Bell size={28} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="my"
        options={{
          title: "MY",
          tabBarIcon: ({ color }) => (
            <User size={28} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
