import { Text, View } from "react-native";

import { AppScrollContent } from "@/components/AppScrollContent";

export default function MealScreen() {
  return (
    <View className="flex-1 bg-[#F3F4F6]">
      <AppScrollContent contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}>
        <Text className="text-2xl font-bold text-center">학식</Text>
      </AppScrollContent>
    </View>
  );
}
