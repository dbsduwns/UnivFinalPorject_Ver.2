import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { Megaphone, ChevronRight } from "lucide-react-native";
import { Notice } from "@/features/auth/api/types";

type NoticeCardProps = {
    notices: Notice[];
    isLoading: boolean;
};


const categoryBadgeStyles: Record<
  string,
  { backgroundColor: string; color: string }
> = {
  "학사": { backgroundColor: "#DBEAFE", color: "#1E40AF" },
  "장학": { backgroundColor: "#D1FAE5", color: "#065F46" },
  "학습/상담": { backgroundColor: "#F3E8FF", color: "#6B21A8" },
  "취업/창업": { backgroundColor: "#FEF3C7", color: "#92400E" },
};

const defaultBadgeStyle = {
    backgroundColor: "#DBEAFE",
    color: "#1E40AF",
};

export const NoticeCard = ({ notices, isLoading }: NoticeCardProps) => {

    const NoticeHref = "/(app)/(tabs)/notice";

    return (
        <View
            className="NoticeCard justify-center flex-col"
            style={{
                backgroundColor: 'white',
                borderWidth: 1,
                borderRadius: 15,
                borderColor: '#E5E7EB',
                width: "100%",
            }}>
            <View
                className="NoiticeCardTitle flex-row justify-between mx-6 mt-6">
                <Megaphone 
                    className="IconMegaphone mr-2 mt-1 "
                    color={'#1aaedb'}
                    size={ 28 }/>
                <Text
                    className="Title"
                    style={{ fontSize: 15, fontWeight: 'bold' }}>
                    공지사항
                </Text>
                <Pressable 
                    className="flex-row"
                    key={NoticeHref}
                    onPress={() => router.push(NoticeHref)}>
                    <Text
                        style={{
                            color: '#1aaedb',
                            fontSize: 12
                        }}>
                        전체보기
                    </Text>
                    <ChevronRight color={'#1aaedb'}/>
                </Pressable>
            </View>
            {isLoading ? (
                <View className="my-6 mx-6">
                    <Text>공지사항을 불러오는 중...</Text>
                </View>
            ) : notices.length === 0 ? (
                <View className="my-6 mx-6">
                    <Text>표시할 공지사항이 없습니다.</Text>
                </View>
            ) : (
                notices.map((notice) => {
                    const badgeStyle = categoryBadgeStyles[notice.category] ?? defaultBadgeStyle;
                
                    return (
                        <View key={notice.id}>
                                <View
                                    className="NoticeContentsWrapper flex-row my-6">
                                    <Text
                                        className="m-3 ml-6 px-5"
                                        style={{
                                            fontWeight: 'bold' ,
                                            backgroundColor: badgeStyle.backgroundColor,
                                            color: badgeStyle.color,
                                            borderRadius: 4}}>
                                        {notice.category}
                                    </Text>
                                    <View
                                        className="ContentsTitle mx-5">
                                        <Text numberOfLines={1}>
                                            {notice.title}
                                        </Text>
                                        <Text>
                                            {notice.published_at ?? notice.crawled_at ?? ""}
                                        </Text>
                                    </View>
                                </View>
                                <View className="h-[1px] bg-gray-100 mx-8"></View>
                        </View>
                    )
                })
            )}
        </View>
    );
}
