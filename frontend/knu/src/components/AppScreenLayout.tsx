import type { PropsWithChildren } from "react";
import { View } from "react-native";

import { AppDrawerMenu } from "@/components/AppDrawer";
import { HomeHeader } from "./HomeHeader";

export const AppScreenLayout = ({ children }: PropsWithChildren) => {
    return (
        <View className="flex-1 bg-[#F3F4F6]">
            <HomeHeader/>
            <View className="flex-1">
                {children}
                <AppDrawerMenu/>
            </View>

        </View>
    )
}
