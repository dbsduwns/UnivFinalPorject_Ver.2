import React, { useState, useMemo, useCallback } from "react";
import { View, Text, TouchableOpacity, FlatList, ScrollView } from "react-native";
import { router } from "expo-router";

import { useNotices } from "@/features/notice/hooks/use_notices";
import { Notice } from "@/features/auth/api/types";


const CATEGORIES = ["전체", "학사", "장학", "학습/상담", "취창업"];

const categoryBadgeStyles: Record<
  string,
  { backgroundColor: string; color: string }
> = {
  "전체": { backgroundColor: "#E5E7EB", color: "#374151" },
  "학사": { backgroundColor: "#DBEAFE", color: "#1E40AF" },
  "장학": { backgroundColor: "#D1FAE5", color: "#065F46" },
  "학습/상담": { backgroundColor: "#F3E8FF", color: "#6B21A8" },
  "취창업": { backgroundColor: "#FEF3C7", color: "#92400E" },
};

const defaultBadgeStyle = {
    backgroundColor: "#DBEAFE",
    color: "#1E40AF",
};

// ✅ 1. 컴포넌트 외부로 추출 (리렌더링 시 재생성 방지 및 메모리 최적화)
const NoticeItem = React.memo(({ item }: { item: Notice }) => {
    
    const badgeStyle = categoryBadgeStyles[item.category] || defaultBadgeStyle;

    return (
        <TouchableOpacity onPress={() => router.push({
            pathname: "/notice/[id]",
            params: { id: item.id.toString() },
        })}>
            <View className="flex-row p-4 items-center bg-white">
                <View 
                    className="w-[78px] px-3 py-1 rounded mr-3 items-center"
                    style={{ backgroundColor: badgeStyle.backgroundColor }}
                >
                    <Text 
                        className="text-xs font-medium"
                        style={{ color: badgeStyle.color, }}    
                    >
                            {item.category}
                    </Text>
                </View>
                <Text className="flex-1 text-base text-gray-800" numberOfLines={1}>
                    {item.title}
                </Text>
            </View>
        </TouchableOpacity>
    );
});

// ✅ 2. 헤더 컴포넌트 외부로 추출
const CategorySelector = React.memo(({ selected, onSelect }: { selected: string, onSelect: (c: string) => void }) => (
    <View className="bg-white py-3 border-b border-gray-100">
        <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 16 }}
        >
            {CATEGORIES.map((category) => {
                const isSelected = selected === category;
                const badgestyle = categoryBadgeStyles[category];
                return (
                    <TouchableOpacity
                        key={category}
                        onPress={() => onSelect(category)}
                        className={`px-4 py-2 rounded-full mr-2 border `}
                        style={[
                            { backgroundColor: "#F9FAFB", borderColor: "#E5E7EB" },
                            isSelected && {
                                backgroundColor: badgestyle.backgroundColor,
                                borderColor: badgestyle.color,
                            }
                        ]}
                    >
                        <Text 
                            className={`font-medium`}
                            style={[
                                { color: "#374151" },
                                isSelected && { color: badgestyle.color },
                            ]}
                        >
                            {category}
                        </Text>
                    </TouchableOpacity>
                );
            })}
        </ScrollView>
    </View>
));

// ✅ 3. 구분선 컴포넌트 외부로 추출
const ItemSeparator = () => <View className="h-[1px] bg-gray-100 mx-4" />;

export default function AllNotice() {
    const [selectedCategory, setSelectedCategory] = useState("전체");
    const { data: notices = [], isLoading } = useNotices();

    // ✅ 4. 필터링 및 정렬 로직 최적화
    const filteredNotices = useMemo(() => {
        let result = selectedCategory === "전체" 
            ? [...notices] 
            : notices.filter(n => n.category === selectedCategory);

        return result.sort((a, b) => {
            const timeA = new Date(a.published_at ?? a.crawled_at ?? 0).getTime();
            const timeB = new Date(b.published_at ?? b.crawled_at ?? 0).getTime();
            return timeB - timeA;
        });
    }, [notices, selectedCategory]);

    // ✅ 5. 렌더링 함수 메모이제이션 (FlatList 성능 핵심)
    const renderItem = useCallback(({ item }: { item: Notice }) => (
        <NoticeItem item={item} />
    ), []);

    const handleSelectCategory = useCallback((category: string) => {
        setSelectedCategory(category);
    }, []);

    return (
        <FlatList
            data={filteredNotices}
            renderItem={renderItem}
            keyExtractor={(item) => item.id.toString()}
            // ✅ 6. 안정적인 컴포넌트 참조 전달
            ListHeaderComponent={
                <CategorySelector 
                    selected={selectedCategory} 
                    onSelect={handleSelectCategory} 
                />
            }
            ItemSeparatorComponent={ItemSeparator}
            ListEmptyComponent={
                <View className="py-20 items-center">
                    <Text className="text-gray-400">해당 카테고리의 공지가 없습니다.</Text>
                </View>
            }
            // ✅ 성능 향상을 위한 추가 설정
            removeClippedSubviews={true} // 화면 밖 아이템 메모리 해제
            initialNumToRender={10} 
            maxToRenderPerBatch={10}
            windowSize={5}
        />
    );
}
