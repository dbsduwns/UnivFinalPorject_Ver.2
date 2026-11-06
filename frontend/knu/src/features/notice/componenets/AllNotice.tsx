import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { View, Text, TextInput, TouchableOpacity, FlatList, ScrollView, Animated, Pressable, ActivityIndicator } from "react-native";
import { Pin, Plus, Search, X } from "lucide-react-native";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { AdminBadge, NoticeAdmin } from "./NoticeAdmin";
import { router } from "expo-router";

import { useNotices } from "@/features/notice/hooks/use_notices";
import { Notice } from "@/features/notice/types";


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
const NoticeItem = React.memo(function NoticeItem({ item, isAdmin, onManage }: { item: Notice; isAdmin: boolean; onManage: (notice: Notice) => void }) {
    const scale = useRef(new Animated.Value(1)).current;
    const animate = (value: number, duration: number) => Animated.timing(scale, { toValue: value, duration, useNativeDriver: true }).start();
    
    const badgeStyle = categoryBadgeStyles[item.category] || defaultBadgeStyle;

    return (
        <Animated.View style={{ transform: [{ scale }] }}><TouchableOpacity
        accessibilityHint={isAdmin ? "길게 누르면 공지를 관리할 수 있습니다" : undefined}
        delayLongPress={500}
        onPressIn={() => { if (isAdmin) animate(0.97, 450); }}
        onPressOut={() => animate(1, 150)}
        onLongPress={isAdmin ? () => { animate(1, 150); onManage(item); } : undefined}
        onPress={() => router.push({
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
                {item.is_important && <View className="mr-2 flex-row items-center"><Pin size={15} color="#13708D" /><Text className="ml-1 text-xs font-bold text-[#13708D]">고정</Text></View>}
                <Text className="flex-1 text-base text-gray-800" numberOfLines={1}>
                    {item.title}
                </Text>
            </View>
        </TouchableOpacity></Animated.View>
    );
});

// ✅ 2. 헤더 컴포넌트 외부로 추출
const CategorySelector = React.memo(function CategorySelector({ selected, onSelect }: { selected: string, onSelect: (c: string) => void }) { return (
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
); });

// ✅ 3. 구분선 컴포넌트 외부로 추출
const ItemSeparator = () => <View className="h-[1px] bg-gray-100 mx-4" />;

export default function AllNotice() {
    const listRef = useRef<FlatList<Notice>>(null);
    const [searchText, setSearchText] = useState("");
    const [keyword, setKeyword] = useState("");
    useEffect(() => {
        const timer = setTimeout(() => setKeyword(searchText.trim()), 300);
        return () => clearTimeout(timer);
    }, [searchText]);
    const isAdmin = useAuthStore(s => s.user?.is_admin === true);
    const [managedNotice, setManagedNotice] = useState<Notice | null>(null);
    const [creating, setCreating] = useState(false);
    const [selectedCategory, setSelectedCategory] = useState("전체");
    const {
        data: notices = [],
        isLoading,
        isError,
        isFetching,
        isRefetching,
        refetch,
    } = useNotices(keyword);
    useEffect(() => {
        listRef.current?.scrollToOffset({ offset: 0, animated: false });
    }, [keyword, selectedCategory]);

    // ✅ 4. 필터링 및 정렬 로직 최적화
    const filteredNotices = useMemo(() => {
        let result = selectedCategory === "전체" 
            ? [...notices] 
            : notices.filter(n => n.category === selectedCategory);

        return result.sort((a, b) => {
            if (a.is_important !== b.is_important) return Number(b.is_important) - Number(a.is_important);
            const timeA = new Date(a.published_at ?? a.crawled_at ?? 0).getTime();
            const timeB = new Date(b.published_at ?? b.crawled_at ?? 0).getTime();
            return timeB - timeA || b.id - a.id;
        });
    }, [notices, selectedCategory]);

    // ✅ 5. 렌더링 함수 메모이제이션 (FlatList 성능 핵심)
    const renderItem = useCallback(({ item }: { item: Notice }) => (
        <NoticeItem item={item} isAdmin={isAdmin} onManage={setManagedNotice} />
    ), [isAdmin]);

    const handleSelectCategory = useCallback((category: string) => {
        setSelectedCategory(category);
    }, []);

    return (
        <View className="flex-1">
            {isAdmin && <View><AdminBadge /><Text className="text-xs text-gray-500 ml-2 mt-2">공지를 길게 눌러 수정·삭제·상단 고정할 수 있습니다.</Text></View>}
            <View className="flex-row items-center bg-white border border-gray-200 rounded-2xl px-4 my-3">
                <Search size={20} color="#13708D" />
                <TextInput accessibilityLabel="공지 제목 검색" placeholder="공지 제목을 검색해 주세요" placeholderTextColor="#9CA3AF" value={searchText} onChangeText={setSearchText} onSubmitEditing={() => setKeyword(searchText.trim())} returnKeyType="search" className="flex-1 px-3 py-3 text-base text-gray-800" />
                {isFetching && <ActivityIndicator size="small" color="#13708D" />}
                {!!searchText && <Pressable accessibilityRole="button" accessibilityLabel="검색어 지우기" onPress={() => { setSearchText(""); setKeyword(""); }} className="p-2"><X size={18} color="#6B7280" /></Pressable>}
            </View>
        <FlatList
            ref={listRef}
            style={{ marginHorizontal: 20 }}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            contentContainerStyle={{ paddingBottom: isAdmin ? 100 : 24 }}
            data={filteredNotices}
            refreshing={isRefetching}
            onRefresh={() => { void refetch(); }}
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
                    {isLoading ? <ActivityIndicator color="#13708D" /> : isError ? <><Text className="text-gray-500">공지를 불러오지 못했습니다.</Text><Pressable onPress={() => { void refetch(); }} className="p-3"><Text className="text-[#13708D]">다시 시도</Text></Pressable></> : <Text className="text-gray-400">{keyword ? "검색 결과가 없습니다." : "해당 카테고리의 공지가 없습니다."}</Text>}
                </View>
            }
            // ✅ 성능 향상을 위한 추가 설정
            removeClippedSubviews={true} // 화면 밖 아이템 메모리 해제
            initialNumToRender={10} 
            maxToRenderPerBatch={10}
            windowSize={5}
        />
        {isAdmin && <Pressable accessibilityRole="button" accessibilityLabel="공지 등록" onPress={() => setCreating(true)} className="absolute left-0 bottom-5 w-14 h-14 rounded-full bg-[#13708D] items-center justify-center shadow-lg" style={{ elevation: 5 }}><Plus size={28} color="white" /></Pressable>}
        {isAdmin && (creating || managedNotice) && <NoticeAdmin key={creating ? "create" : managedNotice?.id} notice={managedNotice ? notices.find(item => item.id === managedNotice.id) ?? managedNotice : null} creating={creating} onPinned={() => listRef.current?.scrollToOffset({ offset: 0, animated: true })} onClose={() => { setCreating(false); setManagedNotice(null); }} />}
        </View>
    );
}
