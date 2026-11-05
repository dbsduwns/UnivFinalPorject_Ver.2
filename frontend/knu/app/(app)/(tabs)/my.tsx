import { Text, View, TouchableOpacity, Switch, Alert, ScrollView, Modal, ActivityIndicator, Linking } from "react-native";
import { useState, useEffect } from "react";
import { useRouter } from "expo-router";
import { 
  User as UserIcon, 
  Bell, 
  ShieldCheck, 
  LogOut, 
  UserMinus,
  ChevronRight, 
  ChevronDown,
  Settings, 
  Key, 
  Mail,
  Info,
  Navigation,
} from "lucide-react-native";

import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuthStore } from "@/features/auth/store/auth-store";
import ProfileEditForm from "@/features/profile/components/ProfileEditForm";
import PasswordVerificationForm from "@/features/profile/components/PasswordVerificationForm";
import PasswordChangeForm from "@/features/profile/components/PasswordChangeForm";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import {
  getNotificationSettingsRequest,
  updateNotificationSettingsRequest,
} from "@/features/auth/api/auth";
import { NotificationSettings } from "@/features/auth/api/types";
import * as WebBrowser from "expo-web-browser";
import * as Google from "expo-auth-session/providers/google";
import { linkGoogleAccount } from "@/features/auth/api/auth";

WebBrowser.maybeCompleteAuthSession();

export default function MyScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const deleteAccount = useAuthStore((s) => s.deleteAccount);
  const [googleLinking, setGoogleLinking] = useState(false);
  const [googleRequest, googleResponse, promptGoogleAsync] = Google.useIdTokenAuthRequest({
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    scopes: ["openid", "profile", "email"],
  });

  // 모달 상태
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [isPasswordChangeModalVisible, setIsPasswordChangeModalVisible] = useState(false);
  const closeModal = () => setIsEditModalVisible(false);

  // 알림 설정 상태
  const [notifSettings, setNotifSettings] = useState<NotificationSettings | null>(null);
  const [isSettingsLoading, setIsSettingsLoading] = useState(true);
  const [isNotificationSettingsExpanded, setIsNotificationSettingsExpanded] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  // 비밀번호 인증 상태 확인
  const [isPasswordVerified, setIsPasswordVerified] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (googleResponse?.type !== "success") return;
    const idToken = googleResponse.authentication?.idToken ?? googleResponse.params?.id_token;
    if (!idToken) {
      Alert.alert("연결 실패", "Google 인증 토큰을 받지 못했습니다.");
      return;
    }
    void (async () => {
      setGoogleLinking(true);
      try {
        await linkGoogleAccount(idToken);
        Alert.alert("연결 완료", "Google 계정이 연결되었습니다.");
      } catch (error: any) {
        Alert.alert("연결 실패", error?.response?.data?.detail ?? "Google 계정 연결에 실패했습니다.");
      } finally { setGoogleLinking(false); }
    })();
  }, [googleResponse]);

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

  const handleDeleteAccount = () => {
    Alert.alert(
      "회원 탈퇴",
      "계정, 시간표, 채팅, 게시글·댓글, 설정 등 모든 데이터가 영구 삭제됩니다. 이 작업은 되돌릴 수 없습니다.",
      [
        { text: "취소", style: "cancel" },
        {
          text: "탈퇴하기",
          style: "destructive",
          onPress: async () => {
            try {
              setIsDeletingAccount(true);
              await deleteAccount();
              router.replace("/login");
            } catch (error) {
              console.error("Failed to delete account:", error);
              Alert.alert("회원 탈퇴 실패", "잠시 후 다시 시도해주세요.");
            } finally {
              setIsDeletingAccount(false);
            }
          },
        },
      ]
    );
  };

  if (!user) return null;


  return (
    <AppScreenLayout>
      <ScrollView className="flex-1 bg-gray-50">
        {/* 상단 프로필 영역 */}
        <View 
          className="bg-white px-6 pt-12 pb-8 rounded-b-[40px] shadow-sm"
          style={{ paddingTop: insets.top, height: insets.top + 76 }}  
        >
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
          {/* 등교 설정 */}
          <SectionTitle title="등교 설정" />
          <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
            <SettingLink
              icon={<Navigation size={20} color="#13708D" />}
              title="집 주소 및 등교 경로 설정"
              onPress={() => router.push("/(app)/commute-settings")}
            />
          </View>
          
          {/* 알림 설정 */}
          <View className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 mb-6">
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityState={{ expanded: isNotificationSettingsExpanded }}
              onPress={() => setIsNotificationSettingsExpanded((expanded) => !expanded)}
              className="flex-row items-center px-5 py-4"
            >
              <View className="w-8"><Bell size={20} color="#4B5563" /></View>
              <Text className="flex-1 ml-1 font-medium text-gray-700">알림 설정</Text>
              {isNotificationSettingsExpanded ? <ChevronDown size={18} color="#9CA3AF" /> : <ChevronRight size={18} color="#D1D5DB" />}
            </TouchableOpacity>
            {isNotificationSettingsExpanded && (
              <>
                <View className="h-[1px] bg-gray-50 mx-4" />
                {isSettingsLoading ? (
                  <View className="py-8 items-center justify-center">
                    <ActivityIndicator color="#2563eb" />
                  </View>
                ) : notifSettings ? (
                  <>
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="셔틀버스 크롤링 업데이트 알림"
                  value={notifSettings.shuttle_alert}
                  onValueChange={() => toggleSetting("shuttle_alert")}
                />
                <View className="h-[1px] bg-gray-50 mx-4" />
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="식단 크롤링 업데이트 알림"
                  value={notifSettings.cafeteria_alert}
                  onValueChange={() => toggleSetting("cafeteria_alert")}
                />
                <View className="h-[1px] bg-gray-50 mx-4" />
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="공지사항 크롤링 업데이트 알림"
                  value={notifSettings.notice_alert}
                  onValueChange={() => toggleSetting("notice_alert")}
                />
                <View className="h-[1px] bg-gray-50 mx-4" />
                <SettingToggle
                  icon={<Bell size={20} color="#4B5563" />}
                  title="1:1 메시지 알림"
                  value={notifSettings.message_alert}
                  onValueChange={() => toggleSetting("message_alert")}
                />
                  </>
                ) : (
                  <Text className="px-5 py-6 text-center text-sm text-gray-500">알림 설정을 불러오지 못했습니다.</Text>
                )}
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
              onPress={() => setIsPasswordChangeModalVisible(true)}
            />
            <View className="h-[1px] bg-gray-50 mx-4" />
            <SettingLink
              icon={<ShieldCheck size={20} color={user.student_verified_at ? "#16A34A" : "#4B5563"} />}
              title={user.student_verified_at ? "학생 인증 완료" : "학생 인증"}
              onPress={() => {
                if (user.student_verified_at) {
                  Alert.alert("학생 인증", "학생 인증이 완료된 계정입니다.");
                } else {
                  router.push("/(app)/account-student-verification");
                }
              }}
            />
            <View className="h-[1px] bg-gray-50 mx-4" />
            <SettingLink
              icon={<Mail size={20} color="#4B5563" />}
              title={googleLinking ? "Google 연결 중..." : "Google 계정 연결"}
              disabled={googleLinking || !googleRequest}
              onPress={() => void promptGoogleAsync()}
            />
            <View className="h-[1px] bg-gray-50 mx-4" />
            <SettingLink
              icon={<UserMinus size={20} color="#EF4444" />}
              title={isDeletingAccount ? "회원 탈퇴 처리 중..." : "회원 탈퇴"}
              titleColor="text-red-500"
              disabled={isDeletingAccount}
              onPress={handleDeleteAccount}
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
                  onPress={async () => {
                    const adminUrl = "https://univfinalporjectver2-admin-web.vercel.app";

                    const supported = await Linking.canOpenURL(adminUrl);
                    if (!supported) {
                      Alert.alert("접속 실패", "관리자 웹페이지를 열 수 없습니다.");
                      return;
                    }

                    await Linking.openURL(adminUrl);
                  }}
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
      >
        {isPasswordVerified ? (
          <ProfileEditForm onClose={closeModal}/>
        ) : (
          <PasswordVerificationForm 
            onVerified={() => setIsPasswordVerified(true)}
            onClose={closeModal}
          />
        )}
      </Modal>

      <Modal
        visible={isPasswordChangeModalVisible}
        animationType="slide"
        onRequestClose={() => setIsPasswordChangeModalVisible(false)}
      >
        <PasswordChangeForm
          onClose={() => setIsPasswordChangeModalVisible(false)}
          onChanged={async () => {
            setIsPasswordChangeModalVisible(false);
            Alert.alert("변경 완료", "비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.");
            await logout();
            router.replace("/login");
          }}
        />
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
  rightText,
  titleColor = "text-gray-700",
  disabled = false,
}: { 
  icon: React.ReactNode, 
  title: string, 
  onPress: () => void,
  rightText?: string,
  titleColor?: string,
  disabled?: boolean,
}) {
  return (
    <TouchableOpacity 
      onPress={onPress}
      disabled={disabled}
      className="flex-row items-center px-5 py-4 active:bg-gray-50"
    >
      <View className="w-8">{icon}</View>
      <Text className={`flex-1 ${titleColor} font-medium ml-1`}>{title}</Text>
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
