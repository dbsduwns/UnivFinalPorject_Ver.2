import { AIAskBar } from "@/components/AIAskBar";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import { AppScrollContent } from "@/components/AppScrollContent";
import { FaqTag } from "@/components/FaqTag";
import { NoticeCard } from "@/components/NoticeCard";
import { QuickMenu } from "@/components/QuickMenu";
import { TodaySchedule } from "@/components/TodaySchedule";
import { useNotices } from "@/features/notice/hooks/use_notices";

export default function HomeScreen() {
  const { data: notices = [], isLoading } = useNotices();

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <AIAskBar/>
        <FaqTag/>
        <TodaySchedule/>
        <QuickMenu/>
        <NoticeCard notices={notices.slice(0, 3)} isLoading={isLoading}/>
      </AppScrollContent>
    </AppScreenLayout>
  );
}
