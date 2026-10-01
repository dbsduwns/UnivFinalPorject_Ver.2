import { AIAskBar } from "@/features/home/AIAskBar";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { AppScrollContent } from "@/components/ui/AppScrollContent";
import { FaqTag } from "@/features/home/FaqTag";
import { NoticeCard } from "@/features/notice/componenets/NoticeCard";
import { QuickMenu } from "@/features/home/QuickMenu";
import { TodaySchedule } from "@/features/home/TodaySchedule";
import { useNotices } from "@/features/notice/hooks/use_notices";
import { WelcomeMessage } from "@/features/home/WelcomeMessage";
import { SocialQuickMenu } from "@/features/home/SocialQuickMenu";

export default function HomeScreen() {
  const { data: notices = [], isLoading } = useNotices();

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <WelcomeMessage/>
        <AIAskBar/>
        <TodaySchedule/>
        <QuickMenu/>
        <SocialQuickMenu/>
        <NoticeCard notices={notices.slice(0, 3)} isLoading={isLoading}/>
      </AppScrollContent>
    </AppScreenLayout>
  );
}
