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
  MessageCircle,
  Megaphone,
  Settings,
  Utensils,
  User,
  Users,
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

type DrawerSection = {
  title: string;
  items: DrawerItem[];
};

const AppDrawerContext = createContext<AppDrawerContextValue | null>(null);

const drawerSections: DrawerSection[] = [
  {
    title: "캠퍼스 생활",
    items: [
      { label: "시간표", href: "/(app)/(tabs)/schedule", icon: Calendar },
      { label: "AI 챗봇", href: "/(app)/(tabs)/ai_chat", icon: Bot },
      { label: "공지사항", href: "/(app)/(tabs)/notice", icon: Megaphone },
      { label: "캠퍼스맵", href: "/(app)/(tabs)/campus-map", icon: MapPin },
      { label: "셔틀", href: "/(app)/(tabs)/shuttle", icon: BusFront },
      { label: "학식", href: "/(app)/(tabs)/meal", icon: Utensils },
    ],
  },
  {
    title: "함께하는 캠퍼스",
    items: [
      { label: "쪽지", href: "/(app)/(tabs)/messages", icon: MessageCircle },
      { label: "커뮤니티", href: "/(app)/(tabs)/community", icon: Megaphone },
      { label: "친구", href: "/(app)/(tabs)/friend", icon: Users },
    ],
  },
  {
    title: "설정",
    items: [
      { label: "통학 설정", href: "/(app)/commute-settings", icon: Settings },
      { label: "마이페이지", href: "/(app)/(tabs)/my", icon: User },
    ],
  },
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
          {drawerSections.map((section) => (
            <View key={section.title} className="pb-2">
              <Text className="border-b border-gray-100 px-5 pb-1 pt-5 text-s font-bold uppercase tracking-wider text-gray-500">
                {section.title}
              </Text>
              {section.items.map((item) => {
                const Icon = item.icon;

                return (
                  <Pressable
                    key={item.href}
                    onPress={() => navigateTo(item.href)}
                    className="flex-row items-center px-5 py-4"
                  >
                    <Icon color="#13708d" size={22} />
                    <Text
                      className="ml-3"
                      style={{ fontSize: 15, fontWeight: "600", color: "#111827" }}
                    >
                      {item.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          ))}
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
