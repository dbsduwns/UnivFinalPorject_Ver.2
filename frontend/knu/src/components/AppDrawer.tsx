import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  BackHandler,
  Pressable,
  ScrollView,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { router } from "expo-router";
import {
  Bot,
  BusFront,
  Calendar,
  Home,
  MapPin,
  Megaphone,
  Utensils,
  User,
} from "lucide-react-native";

type AppDrawerContextValue = {
  isOpen: boolean;
  closeDrawer: () => void;
  openDrawer: () => void;
  toggleDrawer: () => void;
};

type DrawerItem = {
  href: string;
  icon: typeof Home;
  label: string;
};

const AppDrawerContext = createContext<AppDrawerContextValue | null>(null);

const drawerItems: DrawerItem[] = [
  { label: "홈", href: "/(app)/(tabs)", icon: Home },
  { label: "시간표", href: "/(app)/(tabs)/schedule", icon: Calendar },
  { label: "AI 챗봇", href: "/(app)/(tabs)/ai_chat", icon: Bot },
  { label: "공지사항", href: "/(app)/(tabs)/notice", icon: Megaphone },
  { label: "마이페이지", href: "/(app)/(tabs)/my", icon: User },
  { label: "셔틀", href: "/(app)/shuttle", icon: BusFront },
  { label: "학식", href: "/(app)/meal", icon: Utensils },
  { label: "캠퍼스맵", href: "/(app)/campus-map", icon: MapPin },
];

export const AppDrawerProvider = ({ children }: PropsWithChildren) => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const subscription = BackHandler.addEventListener(
      "hardwareBackPress",
      () => {
        if (isOpen) {
          setIsOpen(false);
          return true;
        }

        return false;
      }
    );

    return () => subscription.remove();
  }, [isOpen]);

  const value = useMemo(
    () => ({
      isOpen,
      closeDrawer: () => setIsOpen(false),
      openDrawer: () => setIsOpen(true),
      toggleDrawer: () => setIsOpen((prev) => !prev),
    }),
    [isOpen]
  );

  return (
    <AppDrawerContext.Provider value={value}>
      {children}
    </AppDrawerContext.Provider>
  );
};

export const AppDrawerMenu = () => {
  const { isOpen, closeDrawer } = useAppDrawer();
  const { width } = useWindowDimensions();

  const horizontalPadding = width >= 768 ? 32 : 20;
  const contentWidth = Math.min(width - horizontalPadding * 2, 720);
  const drawerWidth = Math.min(contentWidth * 0.82, 340);

  if (!isOpen) return null;

  const navigateTo = (href: string) => {
    closeDrawer();
    router.push(href as never);
  };

  return (
    <View
      className="absolute inset-0 flex-row"
      style={{ zIndex: 50, elevation: 50 }}
    >
      <View
        className="bg-white border-r border-gray-200"
        style={{
          width: drawerWidth,
          height: "100%",
        }}
      >
        <ScrollView>
          {drawerItems.map((item) => {
            const Icon = item.icon;

            return (
              <Pressable
                key={item.href}
                onPress={() => navigateTo(item.href)}
                className="flex-row items-center px-5 py-4"
              >
                <Icon color="#13708d" size={22}/>
                <Text
                  className="ml-3"
                  style={{ fontSize: 15, fontWeight: "600", color: "#111827" }}
                >
                  {item.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>
      <Pressable className="flex-1" onPress={closeDrawer}/>
    </View>
  );
};

export const useAppDrawer = () => {
  const context = useContext(AppDrawerContext);

  if (!context) {
    throw new Error("useAppDrawer must be used inside AppDrawerProvider");
  }

  return context;
};
