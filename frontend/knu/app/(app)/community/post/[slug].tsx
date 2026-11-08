import { useCallback, useEffect, useRef, useState } from "react";
import { useLocalSearchParams, router } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  EllipsisVertical,
  Heart,
  MessageCircle,
  Send,
  ThumbsUp,
  X,
} from "lucide-react-native";
import {
  ActivityIndicator,
  Alert,
  Keyboard,
  KeyboardAvoidingView,
  Modal,
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
  blockCommentAuthor,
  createComment,
  deleteComment,
  getCommentLikeCount,
  getComments,
  getIsCommentLiked,
  getIsPostLiked,
  getPostLikeCount,
  reportComment,
  toggleCommentLike,
  togglePostLike,
  updateComment,
} from "@/features/community/api/community";
import type {
  CommentReportReason,
  CommunityComment,
} from "@/features/community/api/types";
import { useCommunityPost } from "@/features/community/hooks/use-community";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { PostAdminModal } from "@/features/community/components/PostAdminModal";
import { PostUserActionsModal } from "@/features/community/components/PostUserActionsModal";

const BRAND = "#13708D";
const REPORT_REASONS: readonly {
  value: CommentReportReason;
  label: string;
}[] = [
  { value: "abuse", label: "욕설 및 괴롭힘" },
  { value: "hate", label: "혐오 표현" },
  { value: "sexual", label: "성적 콘텐츠" },
  { value: "spam", label: "스팸 및 도배" },
  { value: "personal_info", label: "개인정보 노출" },
  { value: "impersonation", label: "사칭" },
  { value: "illegal", label: "불법 콘텐츠" },
  { value: "other", label: "기타" },
];

export default function CommunityPostScreen() {
  const isAdmin = useAuthStore(s => s.user?.is_admin === true);
  const [managingPost, setManagingPost] = useState(false);
  const [postActionsOpen, setPostActionsOpen] = useState(false);
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{ slug?: string | string[] }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const postQuery = useCommunityPost(slug);
  const post = postQuery.data;
  const [commentText, setCommentText] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [replyTarget, setReplyTarget] = useState<CommunityComment | null>(null);
  const [menuComment, setMenuComment] = useState<CommunityComment | null>(null);
  const [editingComment, setEditingComment] = useState<CommunityComment | null>(null);
  const [editText, setEditText] = useState("");
  const [editAnonymous, setEditAnonymous] = useState(false);
  const [reportingComment, setReportingComment] = useState<CommunityComment | null>(null);
  const [reportReason, setReportReason] = useState<CommentReportReason>("abuse");
  const [reportDescription, setReportDescription] = useState("");
  const screenContentRef = useRef<View>(null);
  const keyboardTopRef = useRef<number | null>(null);
  const [keyboardOverlap, setKeyboardOverlap] = useState(0);
  const [keyboardVisible, setKeyboardVisible] = useState(false);

  const measureKeyboardOverlap = useCallback(() => {
    const keyboardTop = keyboardTopRef.current;
    if (keyboardTop === null) return;

    screenContentRef.current?.measureInWindow((_x, y, _width, height) => {
      if (keyboardTopRef.current !== keyboardTop) return;
      setKeyboardOverlap(Math.max(0, Math.ceil(y + height - keyboardTop)));
    });
  }, []);

  useEffect(() => {
    if (Platform.OS !== "android") return;

    let frameId: number | null = null;
    const scheduleMeasurement = () => {
      if (frameId !== null) cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        frameId = null;
        measureKeyboardOverlap();
      });
    };

    const showSubscription = Keyboard.addListener("keyboardDidShow", (event) => {
      keyboardTopRef.current = event.endCoordinates.screenY;
      setKeyboardVisible(true);
      scheduleMeasurement();
    });
    const hideSubscription = Keyboard.addListener("keyboardDidHide", () => {
      keyboardTopRef.current = null;
      setKeyboardVisible(false);
      setKeyboardOverlap(0);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
      if (frameId !== null) cancelAnimationFrame(frameId);
    };
  }, [measureKeyboardOverlap]);

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
        parent_comment_id: replyTarget?.id ?? null,
        is_anonymous: isAnonymous,
      }),
    onSuccess: () => {
      setCommentText("");
      setReplyTarget(null);
      void queryClient.invalidateQueries({ queryKey: commentsKey });
    },
    onError: (error) => Alert.alert("댓글 작성 실패", getAxiosErrorMessage(error)),
  });

  const submitComment = () => {
    if (!commentText.trim() || commentMutation.isPending || !post) return;
    commentMutation.mutate();
  };

  const updateCommentMutation = useMutation({
    mutationFn: () =>
      updateComment(post!.id, editingComment!.id, {
        content: editText.trim(),
        is_anonymous: editAnonymous,
      }),
    onSuccess: () => {
      setEditingComment(null);
      setEditText("");
      void queryClient.invalidateQueries({ queryKey: commentsKey });
    },
    onError: (error) => Alert.alert("댓글 수정 실패", getAxiosErrorMessage(error)),
  });

  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: number) => deleteComment(post!.id, commentId),
    onSuccess: () => {
      setMenuComment(null);
      void queryClient.invalidateQueries({ queryKey: commentsKey });
    },
    onError: (error) => Alert.alert("댓글 삭제 실패", getAxiosErrorMessage(error)),
  });

  const reportCommentMutation = useMutation({
    mutationFn: () =>
      reportComment(reportingComment!.id, {
        reason: reportReason,
        description: reportDescription.trim() || null,
      }),
    onSuccess: () => {
      setReportingComment(null);
      setReportDescription("");
      Alert.alert("신고 접수 완료", "신고가 접수되었습니다.");
    },
    onError: (error) => Alert.alert("신고 실패", getAxiosErrorMessage(error)),
  });

  const blockCommentAuthorMutation = useMutation({
    mutationFn: (commentId: number) => blockCommentAuthor(commentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: commentsKey });
      Alert.alert("차단 완료", "작성자의 댓글이 더 이상 표시되지 않습니다.");
    },
    onError: (error) => Alert.alert("작성자 차단 실패", getAxiosErrorMessage(error)),
  });

  const startEditing = (comment: CommunityComment) => {
    setMenuComment(null);
    setEditingComment(comment);
    setEditText(comment.content);
    setEditAnonymous(comment.is_anonymous);
  };

  const confirmDelete = (comment: CommunityComment) => {
    setMenuComment(null);
    Alert.alert("댓글 삭제", "이 댓글을 삭제할까요?", [
      { text: "취소", style: "cancel" },
      {
        text: "삭제",
        style: "destructive",
        onPress: () => deleteCommentMutation.mutate(comment.id),
      },
    ]);
  };

  const openReport = (comment: CommunityComment) => {
    setMenuComment(null);
    setReportReason("abuse");
    setReportDescription("");
    setReportingComment(comment);
  };

  const confirmBlock = (comment: CommunityComment) => {
    setMenuComment(null);
    Alert.alert(
      "작성자 차단",
      "이 작성자를 차단할까요? 차단한 작성자의 댓글은 더 이상 표시되지 않습니다.",
      [
        { text: "취소", style: "cancel" },
        {
          text: "차단",
          style: "destructive",
          onPress: () => blockCommentAuthorMutation.mutate(comment.id),
        },
      ]
    );
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
    <View className="flex-1 bg-[#F4F6F8]">
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
        {(isAdmin || post.is_mine) && <Pressable accessibilityLabel="게시글 관리" onPress={() => setManagingPost(true)} className="h-11 px-3 items-center justify-center rounded-xl bg-cyan-50"><Text className="font-bold text-[#13708D]">{isAdmin ? "관리" : "메뉴"}</Text></Pressable>}
        {!isAdmin && !post.is_mine && <Pressable accessibilityLabel="게시글 메뉴" onPress={() => setPostActionsOpen(true)} className="w-11 h-11 items-center justify-center"><EllipsisVertical size={22} color="#64748B" /></Pressable>}
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View
          ref={screenContentRef}
          className="flex-1"
          style={Platform.OS === "android" ? { paddingBottom: keyboardVisible ? keyboardOverlap + 20 : 0 } : undefined}
          onLayout={Platform.OS === "android" ? measureKeyboardOverlap : undefined}
        >
        <View className="flex-1" style={{ minHeight: 0 }}>
          <ScrollView
            className="flex-1"
            contentContainerStyle={{ paddingBottom: 24 }}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="none"
          >
        <View className="bg-white px-5 pt-6 pb-5 border-b border-gray-200">
          <View className="flex-row items-center">
            <Text className="text-sm font-extrabold text-[#13708D]">{post.author_name}</Text>
            <Text className="text-xs text-gray-300 mx-2">•</Text>
            <Text className="text-xs text-gray-400">
              {new Date(post.created_at).toLocaleString("ko-KR")}
            </Text>
          </View>
          {(post.is_hidden || post.is_pinned) && <Text className="text-xs font-bold text-[#13708D] mt-3">{[post.is_pinned ? "상단 고정" : "", post.is_hidden ? "숨김 처리됨 (관리자에게만 표시)" : ""].filter(Boolean).join(" · ")}</Text>}
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
            commentsQuery.data.map((comment) => (
              <CommentCard
                key={comment.id}
                comment={comment}
                postId={post.id}
                commentsKey={commentsKey}
                onReply={setReplyTarget}
                onOpenMenu={setMenuComment}
              />
            ))
          ) : (
            <View className="py-10 items-center">
              <Text className="text-sm text-gray-400">첫 댓글을 남겨보세요.</Text>
            </View>
          )}
        </View>
          </ScrollView>
        </View>

        <View
          className="shrink-0 bg-white border-t border-gray-200 px-4 pt-3"
          style={{ paddingBottom: Math.max(insets.bottom, 12) }}
        >
        {replyTarget ? (
          <View className="flex-row items-center justify-between mb-2 px-1">
            <Text className="flex-1 text-xs font-bold text-[#13708D]" numberOfLines={1}>
              {replyTarget.author_name}님에게 답글 작성 중
            </Text>
            <Pressable
              accessibilityLabel="답글 작성 취소"
              onPress={() => setReplyTarget(null)}
              className="w-7 h-7 items-center justify-center rounded-full active:bg-gray-100"
            >
              <X size={16} color="#64748B" />
            </Pressable>
          </View>
        ) : null}
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
            placeholder={replyTarget ? "답글을 입력하세요" : "댓글을 입력하세요"}
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
        </View>
      </KeyboardAvoidingView>

      <Modal
        visible={Boolean(menuComment)}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuComment(null)}
      >
        <Pressable
          className="flex-1 bg-black/40 justify-end"
          onPress={() => setMenuComment(null)}
        >
          <Pressable
            className="bg-white rounded-t-3xl px-5 pt-3"
            style={{ paddingBottom: Math.max(insets.bottom, 16) }}
            onPress={(event) => event.stopPropagation()}
          >
            <View className="w-10 h-1 rounded-full bg-gray-300 self-center mb-4" />
            {menuComment?.is_mine ? (
              <>
                <Pressable
                  className="h-14 justify-center px-2 border-b border-gray-100"
                  onPress={() => menuComment && startEditing(menuComment)}
                >
                  <Text className="text-base font-bold text-gray-800">수정</Text>
                </Pressable>
                <Pressable
                  className="h-14 justify-center px-2"
                  onPress={() => menuComment && confirmDelete(menuComment)}
                >
                  <Text className="text-base font-bold text-red-500">삭제</Text>
                </Pressable>
                <Pressable
                  className="h-12 mt-2 rounded-2xl bg-gray-100 items-center justify-center"
                  onPress={() => setMenuComment(null)}
                >
                  <Text className="text-sm font-extrabold text-gray-600">취소</Text>
                </Pressable>
              </>
            ): (
              <>
                <Pressable
                  className="h-14 justify-center px-2 border-b border-gray-100"
                  onPress={() => menuComment && openReport(menuComment)}
                >
                  <Text className="text-base font-bold text-gray-800">신고</Text>
                </Pressable>
                <Pressable
                  className="h-14 justify-center px-2"
                  onPress={() => menuComment && confirmBlock(menuComment)}
                >
                  <Text className="text-base font-bold text-red-500">작성자 차단</Text>
                </Pressable>
                <Pressable
                  className="h-12 mt-2 rounded-2xl bg-gray-100 items-center justify-center"
                  onPress={() => setMenuComment(null)}
                >
                  <Text className="text-sm font-extrabold text-gray-600">취소</Text>
                </Pressable>
              </>
            )
              }
          </Pressable>
        </Pressable>
      </Modal>

      {(isAdmin || post.is_mine) && managingPost && <PostAdminModal allowOwner post={post} onClose={() => setManagingPost(false)} onDeleted={() => router.replace({ pathname: "/(app)/community/[board]", params: { board: post.board_slug } })} />}
      {postActionsOpen && <PostUserActionsModal post={post} onClose={() => setPostActionsOpen(false)} />}

      <Modal
        visible={Boolean(reportingComment)}
        transparent
        animationType="slide"
        onRequestClose={() => setReportingComment(null)}
      >
        <KeyboardAvoidingView
          className="flex-1 bg-black/40 justify-end"
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View
            className="bg-white rounded-t-3xl px-5 pt-5"
            style={{ paddingBottom: Math.max(insets.bottom, 16), maxHeight: "85%" }}
          >
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-lg font-extrabold text-gray-900">댓글 신고</Text>
              <Pressable
                accessibilityLabel="댓글 신고 닫기"
                onPress={() => setReportingComment(null)}
                className="w-9 h-9 rounded-full bg-gray-100 items-center justify-center"
              >
                <X size={18} color="#475569" />
              </Pressable>
            </View>

            <Text className="text-sm font-bold text-gray-700 mb-2">신고 사유</Text>
            <ScrollView
              className="shrink-0"
              style={{ maxHeight: 280 }}
              keyboardShouldPersistTaps="handled"
            >
              {REPORT_REASONS.map((reason) => {
                const selected = reportReason === reason.value;
                return (
                  <Pressable
                    key={reason.value}
                    onPress={() => setReportReason(reason.value)}
                    className={`h-12 px-4 mb-2 rounded-2xl flex-row items-center justify-between ${
                      selected ? "bg-cyan-50 border border-[#13708D]" : "bg-gray-100"
                    }`}
                  >
                    <Text
                      className={`text-sm font-bold ${
                        selected ? "text-[#13708D]" : "text-gray-600"
                      }`}
                    >
                      {reason.label}
                    </Text>
                    <View
                      className={`w-5 h-5 rounded-full border-2 items-center justify-center ${
                        selected ? "border-[#13708D]" : "border-gray-300"
                      }`}
                    >
                      {selected ? <View className="w-2.5 h-2.5 rounded-full bg-[#13708D]" /> : null}
                    </View>
                  </Pressable>
                );
              })}
            </ScrollView>

            <Text className="text-sm font-bold text-gray-700 mt-2 mb-2">
              상세 내용 {reportReason === "other" ? "(필수)" : "(선택)"}
            </Text>
            <TextInput
              value={reportDescription}
              onChangeText={setReportDescription}
              placeholder="신고 내용을 입력해주세요"
              placeholderTextColor="#94A3B8"
              multiline
              maxLength={1000}
              textAlignVertical="top"
              className="min-h-24 max-h-36 rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-900"
            />
            <Pressable
              onPress={() => reportCommentMutation.mutate()}
              disabled={
                reportCommentMutation.isPending ||
                (reportReason === "other" && !reportDescription.trim())
              }
              className="h-12 mt-4 rounded-2xl bg-[#13708D] items-center justify-center disabled:opacity-40"
            >
              {reportCommentMutation.isPending ? (
                <ActivityIndicator color="white" size="small" />
              ) : (
                <Text className="text-sm font-extrabold text-white">신고하기</Text>
              )}
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      <Modal
        visible={Boolean(editingComment)}
        transparent
        animationType="slide"
        onRequestClose={() => setEditingComment(null)}
      >
        <KeyboardAvoidingView
          className="flex-1 bg-black/40 justify-end"
          behavior="padding"
        >
          <View
            className="bg-white rounded-t-3xl px-5 pt-5"
            style={{ paddingBottom: Math.max(insets.bottom, 16) }}
          >
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-lg font-extrabold text-gray-900">댓글 수정</Text>
              <Pressable
                accessibilityLabel="댓글 수정 닫기"
                onPress={() => setEditingComment(null)}
                className="w-9 h-9 rounded-full bg-gray-100 items-center justify-center"
              >
                <X size={18} color="#475569" />
              </Pressable>
            </View>
            <TextInput
              value={editText}
              onChangeText={setEditText}
              placeholder="댓글을 입력하세요"
              placeholderTextColor="#94A3B8"
              multiline
              autoFocus
              className="min-h-28 max-h-48 rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-900"
              textAlignVertical="top"
            />
            <View className="flex-row items-center justify-between mt-4">
              <Pressable
                onPress={() => setEditAnonymous((value) => !value)}
                className={`px-3 py-2 rounded-full ${editAnonymous ? "bg-cyan-100" : "bg-gray-100"}`}
              >
                <Text
                  className={`text-xs font-bold ${editAnonymous ? "text-[#13708D]" : "text-gray-500"}`}
                >
                  익명 {editAnonymous ? "ON" : "OFF"}
                </Text>
              </Pressable>
              <Pressable
                onPress={() => updateCommentMutation.mutate()}
                disabled={!editText.trim() || updateCommentMutation.isPending}
                className="h-11 px-6 rounded-2xl bg-[#13708D] items-center justify-center disabled:opacity-40"
              >
                {updateCommentMutation.isPending ? (
                  <ActivityIndicator color="white" size="small" />
                ) : (
                  <Text className="text-sm font-extrabold text-white">수정 완료</Text>
                )}
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

type CommentCardProps = {
  comment: CommunityComment;
  postId: number;
  commentsKey: readonly unknown[];
  depth?: number;
  onReply: (comment: CommunityComment) => void;
  onOpenMenu: (comment: CommunityComment) => void;
};

function CommentCard({
  comment,
  postId,
  commentsKey,
  depth = 0,
  onReply,
  onOpenMenu,
}: CommentCardProps) {
  const queryClient = useQueryClient();
  const repliesKey = [...commentsKey, comment.id] as const;
  const likeCountKey = ["community", "comment-like-count", comment.id] as const;
  const likedKey = ["community", "comment-liked", comment.id] as const;

  const repliesQuery = useQuery({
    queryKey: repliesKey,
    queryFn: () => getComments(postId, comment.id),
  });
  const likeCountQuery = useQuery({
    queryKey: likeCountKey,
    queryFn: () => getCommentLikeCount(postId, comment.id),
  });
  const likedQuery = useQuery({
    queryKey: likedKey,
    queryFn: () => getIsCommentLiked(postId, comment.id),
  });
  const likeMutation = useMutation({
    mutationFn: () => toggleCommentLike(postId, comment.id),
    onSuccess: (result) => {
      queryClient.setQueryData(likeCountKey, result.like_count);
      queryClient.setQueryData(likedKey, result.liked);
    },
    onError: (error) => Alert.alert("좋아요 처리 실패", getAxiosErrorMessage(error)),
  });

  return (
    <View className={depth === 0 ? "mb-3" : "mt-2"}>
      <View className="bg-white rounded-2xl border border-gray-200 px-4 py-4">
        <View className="flex-row items-start justify-between">
          <View className="flex-1 flex-row items-center pr-2">
            <Text className="text-xs font-extrabold text-[#13708D]">{comment.author_name}</Text>
            <Text className="text-xs text-gray-300 mx-2">•</Text>
            <Text className="text-xs text-gray-400" numberOfLines={1}>
              {new Date(comment.commented_at).toLocaleString("ko-KR")}
            </Text>
          </View>
          <View className="flex-row items-center -mt-2 -mr-2">
            <Pressable
              accessibilityLabel="대댓글 작성"
              onPress={() => onReply(comment)}
              className="w-9 h-9 rounded-full items-center justify-center active:bg-gray-100"
            >
              <MessageCircle size={17} color="#64748B" />
            </Pressable>
            <Pressable
              accessibilityLabel={likedQuery.data ? "댓글 좋아요 취소" : "댓글 좋아요"}
              onPress={() => likeMutation.mutate()}
              disabled={likeMutation.isPending}
              className="min-w-9 h-9 px-1 rounded-full flex-row items-center justify-center active:bg-gray-100"
            >
              <ThumbsUp
                size={17}
                color={likedQuery.data ? BRAND : "#64748B"}
                fill={likedQuery.data ? BRAND : "transparent"}
              />
              {(likeCountQuery.data ?? 0) > 0 ? (
                <Text className="ml-1 text-[11px] font-bold text-gray-500">
                  {likeCountQuery.data}
                </Text>
              ) : null}
            </Pressable>
            <Pressable
              accessibilityLabel="댓글 메뉴"
              onPress={() => onOpenMenu(comment)}
              className="w-9 h-9 rounded-full items-center justify-center active:bg-gray-100"
            >
              <EllipsisVertical size={18} color="#64748B" />
            </Pressable>
          </View>
        </View>
        <Text className="text-sm leading-6 text-gray-700 mt-2">{comment.content}</Text>
      </View>

      {repliesQuery.data?.length ? (
        <View className="ml-5">
          {repliesQuery.data.map((reply, index) => {
            const isLastReply = index === repliesQuery.data.length - 1;

            return (
              <View key={reply.id} className="relative pl-6">
                <View
                  pointerEvents="none"
                  className="absolute left-0 top-0 w-6 h-7"
                  style={{
                    borderLeftWidth: 1.25,
                    borderBottomWidth: 1.25,
                    borderBottomLeftRadius: 14,
                    borderColor: "#CBD5E1",
                  }}
                />
                {!isLastReply ? (
                  <View
                    pointerEvents="none"
                    className="absolute left-0 top-7 bottom-0"
                    style={{ borderLeftWidth: 1.25, borderColor: "#CBD5E1" }}
                  />
                ) : null}
                <CommentCard
                  comment={reply}
                  postId={postId}
                  commentsKey={commentsKey}
                  depth={depth + 1}
                  onReply={onReply}
                  onOpenMenu={onOpenMenu}
                />
              </View>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}
