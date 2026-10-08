import { useState } from "react";
import { useLocalSearchParams, router } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Heart, MessageCircle, Send } from "lucide-react-native";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import {
  createComment,
  getComments,
  getIsPostLiked,
  getPostLikeCount,
  togglePostLike,
} from "@/features/community/api/community";
import type { CommunityComment } from "@/features/community/api/types";
import { useCommunityPost } from "@/features/community/hooks/use-community";

const BRAND = "#13708D";

export default function CommunityPostScreen() {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{ slug?: string | string[] }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const postQuery = useCommunityPost(slug);
  const post = postQuery.data;
  const [commentText, setCommentText] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);

  const commentsKey = ["community", "comments", post?.id] as const;
  const likeCountKey = ["community", "post-like-count", post?.id] as const;
  const likedKey = ["community", "post-liked", post?.id] as const;

  const commentsQuery = useQuery({
    queryKey: commentsKey,
    queryFn: () => getComments(post!.id),
    enabled: Boolean(post?.id),
  });
  const likeCountQuery = useQuery({
    queryKey: likeCountKey,
    queryFn: () => getPostLikeCount(post!.id),
    enabled: Boolean(post?.id),
  });
  const likedQuery = useQuery({
    queryKey: likedKey,
    queryFn: () => getIsPostLiked(post!.id),
    enabled: Boolean(post?.id),
  });

  const likeMutation = useMutation({
    mutationFn: () => togglePostLike(post!.id),
    onSuccess: (result) => {
      queryClient.setQueryData(likeCountKey, result.like_count);
      queryClient.setQueryData(likedKey, result.liked);
    },
    onError: (error) => Alert.alert("좋아요 처리 실패", getAxiosErrorMessage(error)),
  });

  const commentMutation = useMutation({
    mutationFn: () =>
      createComment(post!.id, {
        content: commentText.trim(),
        parent_comment_id: null,
        is_anonymous: isAnonymous,
      }),
    onSuccess: () => {
      setCommentText("");
      void queryClient.invalidateQueries({ queryKey: commentsKey });
    },
    onError: (error) => Alert.alert("댓글 작성 실패", getAxiosErrorMessage(error)),
  });

  const submitComment = () => {
    if (!commentText.trim() || commentMutation.isPending || !post) return;
    commentMutation.mutate();
  };

  if (postQuery.isPending) {
    return (
      <View className="flex-1 bg-[#F4F6F8] items-center justify-center">
        <ActivityIndicator color={BRAND} />
      </View>
    );
  }

  if (postQuery.isError || !post) {
    return (
      <View className="flex-1 bg-[#F4F6F8] items-center justify-center px-8">
        <Text className="text-base font-extrabold text-gray-700">게시물을 불러오지 못했어요</Text>
        <Text className="text-sm text-gray-400 text-center mt-2">
          {getAxiosErrorMessage(postQuery.error)}
        </Text>
        <Pressable onPress={() => router.back()} className="mt-5 px-5 py-3 rounded-2xl bg-[#13708D]">
          <Text className="text-white font-extrabold">돌아가기</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-[#F4F6F8]"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View
        className="bg-white border-b border-gray-200 px-4 flex-row items-end pb-4"
        style={{ paddingTop: insets.top, height: insets.top + 76 }}
      >
        <Pressable
          accessibilityLabel="게시판으로 돌아가기"
          onPress={() => router.back()}
          className="w-11 h-11 rounded-full items-center justify-center active:bg-gray-100"
        >
          <ArrowLeft size={24} color="#1F2937" />
        </Pressable>
        <View className="flex-1 ml-1 justify-center h-11">
          <Text className="text-xl font-extrabold text-gray-900">게시물</Text>
        </View>
      </View>

      <ScrollView className="flex-1" contentContainerStyle={{ paddingBottom: 24 }}>
        <View className="bg-white px-5 pt-6 pb-5 border-b border-gray-200">
          <View className="flex-row items-center">
            <Text className="text-sm font-extrabold text-[#13708D]">{post.author_name}</Text>
            <Text className="text-xs text-gray-300 mx-2">•</Text>
            <Text className="text-xs text-gray-400">
              {new Date(post.created_at).toLocaleString("ko-KR")}
            </Text>
          </View>
          <Text className="text-2xl font-extrabold text-gray-900 mt-4">{post.title}</Text>
          <Text className="text-[15px] leading-7 text-gray-700 mt-5">{post.content}</Text>

          <View className="flex-row mt-7 pt-4 border-t border-gray-100">
            <Pressable
              onPress={() => likeMutation.mutate()}
              disabled={likeMutation.isPending}
              className="flex-row items-center px-3 py-2 rounded-xl bg-gray-50 active:bg-gray-100"
            >
              <Heart
                size={19}
                color={likedQuery.data ? "#EF4444" : "#64748B"}
                fill={likedQuery.data ? "#EF4444" : "transparent"}
              />
              <Text className="ml-1.5 text-sm font-bold text-gray-600">
                {likeCountQuery.data ?? 0}
              </Text>
            </Pressable>
            <View className="flex-row items-center px-3 py-2 ml-2">
              <MessageCircle size={19} color="#64748B" />
              <Text className="ml-1.5 text-sm font-bold text-gray-600">
                {commentsQuery.data?.length ?? 0}
              </Text>
            </View>
          </View>
        </View>

        <View className="px-5 pt-5">
          <Text className="text-lg font-extrabold text-gray-900 mb-3">댓글</Text>
          {commentsQuery.isPending ? (
            <ActivityIndicator color={BRAND} style={{ marginTop: 24 }} />
          ) : commentsQuery.isError ? (
            <Pressable onPress={() => void commentsQuery.refetch()} className="py-8 items-center">
              <Text className="text-sm text-gray-500">댓글을 불러오지 못했어요. 다시 시도</Text>
            </Pressable>
          ) : commentsQuery.data?.length ? (
            commentsQuery.data.map((comment) => <CommentCard key={comment.id} comment={comment} />)
          ) : (
            <View className="py-10 items-center">
              <Text className="text-sm text-gray-400">첫 댓글을 남겨보세요.</Text>
            </View>
          )}
        </View>
      </ScrollView>

      <View
        className="bg-white border-t border-gray-200 px-4 pt-3"
        style={{ paddingBottom: Math.max(insets.bottom, 12) }}
      >
        <View className="flex-row items-center mb-2">
          <Pressable
            onPress={() => setIsAnonymous((value) => !value)}
            className={`px-3 py-1.5 rounded-full ${isAnonymous ? "bg-cyan-100" : "bg-gray-100"}`}
          >
            <Text className={`text-xs font-bold ${isAnonymous ? "text-[#13708D]" : "text-gray-500"}`}>
              익명 {isAnonymous ? "ON" : "OFF"}
            </Text>
          </Pressable>
        </View>
        <View className="flex-row items-end">
          <TextInput
            value={commentText}
            onChangeText={setCommentText}
            placeholder="댓글을 입력하세요"
            placeholderTextColor="#94A3B8"
            multiline
            className="flex-1 min-h-11 max-h-28 rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-900"
          />
          <Pressable
            accessibilityLabel="댓글 등록"
            onPress={submitComment}
            disabled={!commentText.trim() || commentMutation.isPending}
            className="w-11 h-11 ml-2 rounded-full bg-[#13708D] items-center justify-center disabled:opacity-40"
          >
            {commentMutation.isPending ? (
              <ActivityIndicator color="white" size="small" />
            ) : (
              <Send size={19} color="white" />
            )}
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function CommentCard({ comment }: { comment: CommunityComment }) {
  return (
    <View className="bg-white rounded-2xl border border-gray-200 px-4 py-4 mb-3">
      <View className="flex-row items-center">
        <Text className="text-xs font-extrabold text-[#13708D]">{comment.author_name}</Text>
        <Text className="text-xs text-gray-300 mx-2">•</Text>
        <Text className="text-xs text-gray-400">
          {new Date(comment.commented_at).toLocaleString("ko-KR")}
        </Text>
      </View>
      <Text className="text-sm leading-6 text-gray-700 mt-2">{comment.content}</Text>
    </View>
  );
}
