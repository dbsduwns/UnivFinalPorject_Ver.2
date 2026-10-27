import type { PropsWithChildren } from "react";
import { Platform, View } from "react-native";
import { useSegments } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { AppDrawerMenu } from "@/components/ui/AppDrawer";
import { HomeHeader } from "./HomeHeader";

export const AppScreenLayout = ({ children }: PropsWithChildren) => {
    const insets = useSafeAreaInsets();
    const segments: readonly string[] = useSegments();
    // The tab navigator already reserves its bottom area; standalone screens do not.
    const bottomInset = Platform.OS === "android" && !segments.includes("(tabs)") ? insets.bottom : 0;

    return (
        <View className="flex-1 bg-[#F3F4F6]" style={{ paddingBottom: bottomInset }}>
            <HomeHeader/>
            <View className="flex-1">
                {children}
                <AppDrawerMenu/>
            </View>

        </View>
    )
}
