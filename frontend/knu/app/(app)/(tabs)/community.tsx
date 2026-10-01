import type { ReactNode } from "react";
import { router } from "expo-router";
import {
  Award,
  BriefcaseBusiness,
  ChevronRight,
  Flame,
  GraduationCap,
  Heart,
  MessageCircle,
  MessagesSquare,
  Store,
  UsersRound,
} from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  COMMUNITY_BOARDS,
  HOT_POSTS,
  type CommunityPost,
} from "@/features/community/data/community";

const BRAND = "#13708D";

const BOARD_ICONS: Record<string, ReactNode> = {
  free: <MessagesSquare size={24} color={BRAND} />,
  freshman: <GraduationCap size={25} color={BRAND} />,
  graduate: <Award size={24} color={BRAND} />,
  market: <Store size={24} color={BRAND} />,
  club: <UsersRound size={24} color={BRAND} />,
  career: <BriefcaseBusiness size={24} color={BRAND} />,
};

export default function CommunityScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View className="flex-1 bg-[#F4F6F8]">
      <View
        className="bg-white border-b border-gray-200 px-5 justify-end"
        style={{ paddingTop: insets.top, height: insets.top + 88 }}
      >
        <Text className="text-[28px] font-extrabold text-gray-900 pb-6">커뮤니티</Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ paddingTop: 24, paddingBottom: 32 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="mb-8">
          <View className="px-5 flex-row items-center mb-3">
            <Text className="text-xl font-extrabold text-gray-900">HOT 게시물</Text>
            <Flame size={22} color="#F97316" fill="#F97316" style={{ marginLeft: 5 }} />
          </View>

          {HOT_POSTS.length === 0 ? (
            <View className="mx-5 h-40 rounded-3xl bg-white border border-gray-100 items-center justify-center px-6">
              <View className="w-12 h-12 rounded-full bg-orange-50 items-center justify-center">
                <Flame size={23} color="#FDBA74" />
              </View>
              <Text className="text-sm font-extrabold text-gray-600 mt-3">아직 HOT 게시물이 없어요</Text>
              <Text className="text-xs text-gray-400 mt-1.5 text-center">
                인기 게시물이 생기면 이곳에서 바로 확인할 수 있어요.
              </Text>
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 20, gap: 14 }}
            >
              {HOT_POSTS.map((post) => <HotPostCard key={post.id} post={post} />)}
            </ScrollView>
          )}
        </View>

        <View className="px-5">
          <Text className="text-xl font-extrabold text-gray-900 mb-4">게시판 목록</Text>
          <View className="bg-white rounded-3xl border border-gray-200 overflow-hidden">
            {COMMUNITY_BOARDS.map((board, index) => (
              <View key={board.slug}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`${board.title} 열기`}
                  onPress={() =>
                    router.push({
                      pathname: "/(app)/community/[board]",
                      params: { board: board.slug },
                    })
                  }
                  className="h-[82px] px-5 flex-row items-center active:bg-gray-50"
                >
                  <View className="w-12 h-12 rounded-2xl bg-cyan-50 items-center justify-center">
                    {BOARD_ICONS[board.slug]}
                  </View>
                  <Text className="flex-1 ml-4 text-[17px] font-extrabold text-gray-900">
                    {board.title}
                  </Text>
                  <ChevronRight size={22} color="#9CA3AF" />
                </Pressable>
                {index < COMMUNITY_BOARDS.length - 1 && (
                  <View className="h-px bg-gray-200 ml-[84px]" />
                )}
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const HotPostCard = ({ post }: { post: CommunityPost }) => {
  const board = COMMUNITY_BOARDS.find((item) => item.slug === post.boardSlug);

  return (
    <Pressable className="w-[320px] h-44 rounded-3xl bg-white border border-gray-100 p-5 active:bg-gray-50">
      <View className="flex-row items-center">
        <View className="px-3 py-1 rounded-full bg-cyan-50">
          <Text className="text-xs font-extrabold" style={{ color: BRAND }}>
            {board?.title ?? "커뮤니티"}
          </Text>
        </View>
        <View className="ml-auto flex-row items-center">
          <Heart size={15} color="#EF4444" fill="#EF4444" />
          <Text className="ml-1 text-xs font-bold text-gray-500">{post.likeCount}</Text>
          <MessageCircle size={15} color="#94A3B8" style={{ marginLeft: 10 }} />
          <Text className="ml-1 text-xs font-bold text-gray-500">{post.commentCount}</Text>
        </View>
      </View>
      <Text className="text-base font-extrabold text-gray-900 mt-4" numberOfLines={1}>
        {post.title}
      </Text>
      <Text className="text-sm leading-5 text-gray-500 mt-1.5" numberOfLines={2}>
        {post.preview}
      </Text>
    </Pressable>
  );
};
