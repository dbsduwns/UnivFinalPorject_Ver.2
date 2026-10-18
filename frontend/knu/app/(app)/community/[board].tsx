import { useEffect, useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { ArrowLeft, FileText, PenLine, Search, X, Pin, EyeOff, EllipsisVertical, ShieldCheck } from "lucide-react-native";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { PostAdminModal } from "@/features/community/components/PostAdminModal";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import type { CommunityPost } from "@/features/community/api/types";
import { getCommunityBoard } from "@/features/community/data/community";
import { useCommunityPosts } from "@/features/community/hooks/use-community";

const BRAND = "#13708D";

const formatDate = (value: string) =>
  new Date(value).toLocaleDateString("ko-KR", {
    month: "short",
    day: "numeric",
  });

export default function CommunityBoardScreen() {
  const insets = useSafeAreaInsets();
  const isAdmin = useAuthStore(s => s.user?.is_admin === true);
  const [managedPost, setManagedPost] = useState<CommunityPost | null>(null);
  const params = useLocalSearchParams<{ board?: string | string[] }>();
  const slug = Array.isArray(params.board) ? params.board[0] : params.board;
  const board = getCommunityBoard(slug);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedQuery(query.trim()); setPage(0); }, 350);
    return () => clearTimeout(timer);
  }, [query]);

  const postsQuery = useCommunityPosts(slug, debouncedQuery, page * 20);
  const posts = postsQuery.data ?? [];

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
        {isAdmin && <View className="flex-row items-center bg-cyan-50 rounded-full px-3 py-2 mb-1"><ShieldCheck size={14} color={BRAND} /><Text className="ml-1 text-xs font-bold text-[#13708D]">관리자</Text></View>}
      </View>

      <View className="px-5 pt-5 pb-3">
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

      {postsQuery.isPending ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={BRAND} />
          <Text className="text-sm text-gray-500 mt-3">게시물을 불러오고 있어요</Text>
        </View>
      ) : postsQuery.isError ? (
        <View className="flex-1 items-center justify-center px-8">
          <Text className="text-base font-extrabold text-gray-700">게시물을 불러오지 못했어요</Text>
          <Text className="text-sm text-gray-400 text-center mt-2">
            {getAxiosErrorMessage(postsQuery.error)}
          </Text>
          <Pressable
            onPress={() => void postsQuery.refetch()}
            className="mt-5 px-5 py-3 rounded-2xl bg-[#13708D] active:opacity-80"
          >
            <Text className="text-white font-extrabold">다시 시도</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={posts}
          keyExtractor={(post) => String(post.id)}
          renderItem={({ item }) => <PostCard post={item} onManage={isAdmin ? setManagedPost : undefined} />}
          contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 8, paddingBottom: 100, flexGrow: 1 }}
          ItemSeparatorComponent={() => <View className="h-3" />}
          ListFooterComponent={(page > 0 || posts.length === 20) ? <View className="flex-row justify-center items-center py-5"><Pressable disabled={page === 0} onPress={() => setPage(value => value - 1)} className="px-4 py-3 rounded-xl bg-white disabled:opacity-30"><Text className="font-bold text-[#13708D]">이전</Text></Pressable><Text className="mx-4 text-gray-500">{page + 1}</Text><Pressable disabled={posts.length < 20} onPress={() => setPage(value => value + 1)} className="px-4 py-3 rounded-xl bg-white disabled:opacity-30"><Text className="font-bold text-[#13708D]">다음</Text></Pressable></View> : null}
          refreshControl={
            <RefreshControl
              refreshing={postsQuery.isRefetching}
              onRefresh={() => void postsQuery.refetch()}
              tintColor={BRAND}
            />
          }
          ListEmptyComponent={
            <View className="flex-1 min-h-[360px] items-center justify-center">
              <View className="w-16 h-16 rounded-full bg-cyan-50 items-center justify-center">
                {debouncedQuery ? (
                  <Search size={28} color={BRAND} />
                ) : (
                  <FileText size={28} color={BRAND} />
                )}
              </View>
              <Text className="text-base font-extrabold text-gray-700 mt-4">
                {debouncedQuery ? "검색 결과가 없어요" : "아직 작성된 게시물이 없어요"}
              </Text>
              <Text className="text-sm text-gray-400 text-center mt-2">
                {debouncedQuery ? "다른 검색어를 입력해보세요." : "첫 번째 게시물을 작성해보세요."}
              </Text>
            </View>
          }
        />
      )}

      <Pressable
        accessibilityLabel="게시물 작성"
        onPress={() =>
          router.push({
            pathname: "/(app)/community/new",
            params: { board: slug },
          } as never)
        }
        className="absolute right-5 w-14 h-14 rounded-full items-center justify-center shadow-lg"
        style={{ bottom: Math.max(insets.bottom, 20), backgroundColor: BRAND, elevation: 6 }}
      >
        <PenLine size={23} color="white" />
      </Pressable>
      {isAdmin && managedPost && <PostAdminModal key={managedPost.id} post={posts.find(post => post.id === managedPost.id) ?? managedPost} onClose={() => { setManagedPost(null); setPage(0); }} />}
    </View>
  );
}

function PostCard({ post, onManage }: { post: CommunityPost; onManage?: (post: CommunityPost) => void }) {
  return (
    <Pressable
      onLongPress={onManage ? () => onManage(post) : undefined}
      onPress={() =>
        router.push({
          pathname: "/(app)/community/post/[slug]",
          params: { slug: post.slug },
        } as never)
      }
      className="rounded-3xl bg-white border border-gray-200 px-5 py-5 active:bg-gray-50"
    >
      <View className="flex-row items-center">
        {post.is_pinned && <View className="mr-2 flex-row items-center"><Pin size={13} color={BRAND} /><Text className="ml-1 text-xs font-bold text-[#13708D]">고정</Text></View>}
        {post.is_hidden && <View className="mr-2 flex-row items-center"><EyeOff size={13} color="#6B7280" /><Text className="ml-1 text-xs text-gray-500">숨김</Text></View>}
        <Text className="text-xs font-bold text-[#13708D]">{post.author_name}</Text>
        <Text className="text-xs text-gray-300 mx-2">•</Text>
        <Text className="text-xs text-gray-400">{formatDate(post.created_at)}</Text>
        {onManage && <Pressable accessibilityLabel="게시글 관리" onPress={event => { event.stopPropagation(); onManage(post); }} className="ml-auto p-2 -mr-2"><EllipsisVertical size={19} color="#64748B" /></Pressable>}
      </View>
      <Text className="text-[17px] font-extrabold text-gray-900 mt-3" numberOfLines={1}>
        {post.title}
      </Text>
      <Text className="text-sm leading-5 text-gray-500 mt-2" numberOfLines={2}>
        {post.content}
      </Text>
    </Pressable>
  );
}
