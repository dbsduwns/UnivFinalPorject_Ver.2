import { Text, View, TouchableOpacity, Switch, Alert, ScrollView, Modal, ActivityIndicator } from "react-native";
import { useState, useEffect } from "react";
import { useRouter } from "expo-router";
import { 
  User as UserIcon, 
  Bell, 
  ShieldCheck, 
  LogOut, 
  ChevronRight, 
  Settings, 
  Key, 
  Mail,
  Smartphone,
  Info
} from "lucide-react-native";

import { useAuthStore } from "@/features/auth/store/auth-store";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import ChangeUserInfo from "@/components/changeUserInfo";
import { getNotificationSettingsRequest, updateNotificationSettingsRequest } from "@/features/auth/api/auth";
import { NotificationSettings } from "@/features/auth/api/types";

export default function MyScreen() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  // 모달 상태
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);

  // 알림 설정 상태
  const [notifSettings, setNotifSettings] = useState<NotificationSettings | null>(null);
  const [isSettingsLoading, setIsSettingsLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setIsSettingsLoading(true);
      const settings = await getNotificationSettingsRequest();
      setNotifSettings(settings);
    } catch (error) {
      console.error("Failed to fetch notification settings:", error);
    } finally {
      setIsSettingsLoading(false);
    }
  };

  const toggleSetting = async (key: keyof NotificationSettings) => {
    if (!notifSettings) return;

    const newValue = !notifSettings[key];
    
    // UI 즉시 반영 (Optimistic UI)
    setNotifSettings({ ...notifSettings, [key]: newValue });

    try {
      await updateNotificationSettingsRequest({ [key]: newValue });
    } catch (error) {
      console.error(`Failed to update ${key}:`, error);
      // 에러 시 롤백
      setNotifSettings({ ...notifSettings, [key]: !newValue });
      Alert.alert("오류", "설정 변경에 실패했습니다.");
    }
  };

  const handleLogout = () => {
    Alert.alert(
      "로그아웃",
      "정말 로그아웃 하시겠습니까?",
      [
        { text: "취소", style: "cancel" },
        { 
          text: "로그아웃", 
          style: "destructive", 
          onPress: async () => {
            await logout();
            router.replace("/login");
          } 
        },
      ]
    );
  };

  if (!user) return null;

  return (
    <AppScreenLayout>
      <ScrollView className="flex-1 bg-gray-50">
        {/* 상단 프로필 영역 */}
        <View className="bg-white px-6 pt-12 pb-8 rounded-b-[40px] shadow-sm">
          <View className="flex-row items-center">
            <View className="w-20 h-20 bg-blue-100 rounded-full items-center justify-center">
              <UserIcon size={40} color="#2563eb" />
            </View>
            <View className="ml-5 flex-1">
              <View className="flex-row items-center">
                <Text className="text-2xl font-bold text-gray-900">{user.name}</Text>
                {user.is_admin && (
                  <View className="ml-2 bg-blue-600 px-2 py-0.5 rounded-md">
                    <Text className="text-[10px] text-white font-bold">ADMIN</Text>
                  </View>
                )}
              </View>
              <Text className="text-gray-500 mt-1">{user.email}</Text>
              <Text className="text-gray-400 text-sm mt-0.5">
                {user.department || "학과 정보 없음"} · {user.grade ? `${user.grade}학년` : "학년 정보 없음"}
                {user.student_id ? ` · ${user.student_id}` : ""}
              </Text>
            </View>
          </View>
        </View>

        {/* 설정 그룹 */}
        <View className="px-5 mt-6 pb-12">
          
          {/* 알림 설정 */}
          <SectionTitle title="알림 설정" />
          <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
            {isSettingsLoading ? (
              <View className="py-10 items-center justify-center">
                <ActivityIndicator color="#2563eb" />
              </View>
            ) : notifSettings && (
              <>
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="셔틀버스 업데이트 알림"
                  value={notifSettings.shuttle_alert}
                  onValueChange={() => toggleSetting("shuttle_alert")}
                />
                <View className="h-[1px] bg-gray-50 mx-4" />
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="오늘의 식단 업데이트 알림"
                  value={notifSettings.cafeteria_alert}
                  onValueChange={() => toggleSetting("cafeteria_alert")}
                />
                <View className="h-[1px] bg-gray-50 mx-4" />
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="공지사항 업데이트 알림"
                  value={notifSettings.notice_alert}
                  onValueChange={() => toggleSetting("notice_alert")}
                />
              </>
            )}
          </View>

          {/* 계정 관리 */}
          <SectionTitle title="계정 관리" />
          <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
            <SettingLink
              icon={<Settings size={20} color="#4B5563" />}
              title="회원 정보 수정"
              onPress={() => setIsEditModalVisible(true)}
            />
            <View className="h-[1px] bg-gray-50 mx-4" />
            <SettingLink
              icon={<Key size={20} color="#4B5563" />}
              title="비밀번호 변경"
              onPress={() => Alert.alert("준비 중", "비밀번호 변경 기능은 곧 추가됩니다.")}
            />
          </View>

          {/* 관리자 도구 (조건부 렌더링) */}
          {user.is_admin && (
            <>
              <SectionTitle title="시스템 관리" />
              <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
                <SettingLink
                  icon={<ShieldCheck size={20} color="#2563eb" />}
                  title="관리자 페이지 접속"
                  onPress={() => Alert.alert("관리자 페이지", "백엔드 대시보드로 이동합니다.")}
                />
              </View>
            </>
          )}

          {/* 앱 정보 */}
          <SectionTitle title="서비스 정보" />
          <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
            <SettingLink
              icon={<Info size={20} color="#4B5563" />}
              title="앱 버전"
              rightText="v1.0.0"
              onPress={() => {}}
            />
            <View className="h-[1px] bg-gray-50 mx-4" />
            <SettingLink
              icon={<Mail size={20} color="#4B5563" />}
              title="문의하기"
              onPress={() => Alert.alert("문의하기", "yeoju@example.com으로 메일을 보내주세요.")}
            />
          </View>

          {/* 로그아웃 버튼 */}
          <TouchableOpacity 
            onPress={handleLogout}
            className="flex-row items-center justify-center py-4 bg-white rounded-3xl shadow-sm border border-red-50 mt-4"
          >
            <LogOut size={20} color="#EF4444" />
            <Text className="ml-2 text-red-500 font-bold text-lg">로그아웃</Text>
          </TouchableOpacity>
          
          <Text className="text-center text-gray-400 text-xs mt-8 mb-4">
            © 2026 KNU CAMPUS ALL RIGHTS RESERVED.
          </Text>
        </View>
      </ScrollView>

      {/* 회원 정보 수정 모달 */}
      <Modal
        visible={isEditModalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setIsEditModalVisible(false)}
      >
        <ChangeUserInfo onClose={() => setIsEditModalVisible(false)} />
      </Modal>
    </AppScreenLayout>
  );
}

// 서브 컴포넌트: 섹션 타이틀
function SectionTitle({ title }: { title: string }) {
  return <Text className="text-gray-500 font-bold ml-2 mb-2 text-sm uppercase tracking-wider">{title}</Text>;
}

// 서브 컴포넌트: 링크형 설정 항목
function SettingLink({ 
  icon, 
  title, 
  onPress, 
  rightText 
}: { 
  icon: React.ReactNode, 
  title: string, 
  onPress: () => void,
  rightText?: string
}) {
  return (
    <TouchableOpacity 
      onPress={onPress}
      className="flex-row items-center px-5 py-4 active:bg-gray-50"
    >
      <View className="w-8">{icon}</View>
      <Text className="flex-1 text-gray-700 font-medium ml-1">{title}</Text>
      {rightText && <Text className="text-gray-400 mr-2">{rightText}</Text>}
      <ChevronRight size={18} color="#D1D5DB" />
    </TouchableOpacity>
  );
}

// 서브 컴포넌트: 토글형 설정 항목
function SettingToggle({ 
  icon, 
  title, 
  value, 
  onValueChange 
}: { 
  icon: React.ReactNode, 
  title: string, 
  value: boolean, 
  onValueChange: (val: boolean) => void 
}) {
  return (
    <View className="flex-row items-center px-5 py-4">
      <View className="w-8">{icon}</View>
      <Text className="flex-1 text-gray-700 font-medium ml-1">{title}</Text>
      <Switch 
        value={value} 
        onValueChange={onValueChange}
        trackColor={{ false: "#D1D5DB", true: "#93C5FD" }}
        thumbColor={value ? "#2563eb" : "#F3F4F6"}
      />
    </View>
  );
}
