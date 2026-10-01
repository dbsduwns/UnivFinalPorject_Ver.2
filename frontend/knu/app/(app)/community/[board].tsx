import { useMemo, useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  FileText,
  PenLine,
  Search,
  X,
} from "lucide-react-native";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  HOT_POSTS,
  getCommunityBoard,
} from "@/features/community/data/community";

const BRAND = "#13708D";

export default function CommunityBoardScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ board?: string | string[] }>();
  const slug = Array.isArray(params.board) ? params.board[0] : params.board;
  const board = getCommunityBoard(slug);
  const [query, setQuery] = useState("");

  const posts = useMemo(() => {
    const boardPosts = HOT_POSTS.filter((post) => post.boardSlug === slug);
    const keyword = query.trim().toLocaleLowerCase("ko");
    if (!keyword) return boardPosts;
    return boardPosts.filter((post) =>
      `${post.title} ${post.preview}`.toLocaleLowerCase("ko").includes(keyword)
    );
  }, [query, slug]);

  return (
    <View className="flex-1 bg-[#F4F6F8]">
      <View
        className="bg-white border-b border-gray-200 px-4 flex-row items-end pb-4"
        style={{ paddingTop: insets.top, height: insets.top + 76 }}
      >
        <Pressable
          accessibilityLabel="커뮤니티로 돌아가기"
          onPress={() => router.back()}
          className="w-11 h-11 rounded-full items-center justify-center active:bg-gray-100"
        >
          <ArrowLeft size={24} color="#1F2937" />
        </Pressable>
        <View className="flex-1 ml-1 justify-center h-11">
          <Text className="text-xl font-extrabold text-gray-900">
            {board?.title ?? "게시판"}
          </Text>
        </View>
      </View>

      <View className="px-5 pt-5 pb-3 bg-[#F4F6F8]">
        <View className="h-12 rounded-2xl bg-white border border-gray-200 px-4 flex-row items-center">
          <Search size={19} color="#94A3B8" />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={`${board?.title ?? "게시판"}에서 검색`}
            placeholderTextColor="#94A3B8"
            returnKeyType="search"
            className="flex-1 ml-2 text-sm text-gray-900"
          />
          {!!query && (
            <Pressable onPress={() => setQuery("")} className="p-1">
              <X size={17} color="#94A3B8" />
            </Pressable>
          )}
        </View>
      </View>

      <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, flexGrow: 1 }}>
        {posts.length === 0 ? (
          <View className="flex-1 min-h-[360px] items-center justify-center">
            <View className="w-16 h-16 rounded-full bg-cyan-50 items-center justify-center">
              {query ? <Search size={28} color={BRAND} /> : <FileText size={28} color={BRAND} />}
            </View>
            <Text className="text-base font-extrabold text-gray-700 mt-4">
              {query ? "검색 결과가 없어요" : "아직 작성된 게시물이 없어요"}
            </Text>
            <Text className="text-sm text-gray-400 text-center mt-2">
              {query ? "다른 검색어를 입력해보세요." : "첫 번째 게시물을 작성해보세요."}
            </Text>
          </View>
        ) : null}
      </ScrollView>

      <Pressable
        accessibilityLabel="게시물 작성"
        className="absolute right-5 w-14 h-14 rounded-full items-center justify-center shadow-lg"
        style={{ bottom: Math.max(insets.bottom, 20), backgroundColor: BRAND, elevation: 6 }}
      >
        <PenLine size={23} color="white" />
      </Pressable>
    </View>
  );
}
