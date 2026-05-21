import { Text, View } from "react-native";

import { AppScrollContent } from "@/components/AppScrollContent";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import { NoticeCard } from "@/components/NoticeCard";
import { useNotices } from "@/features/notice/hooks/use_notices";

export default function NoticeScreen() {

  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const { data: notices = [], isLoading } = useNotices();

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <NoticeCard notices={notices} isLoading={isLoading} />
      </AppScrollContent>
    </AppScreenLayout>
  );
}