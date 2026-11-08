import { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { Eye, EyeOff, Pencil, Pin, PinOff, Trash2, X } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { getAxiosErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { manageCommunityPost, type ManagePostBody } from "@/features/community/api/admin";
import { deleteCommunityPost, updateCommunityPost } from "@/features/community/api/community";
import type { CommunityPost } from "@/features/community/api/types";

const BRAND = "#13708D";
type Props = { post: CommunityPost; onClose: () => void; onDeleted?: () => void; allowOwner?: boolean };

export function PostAdminModal({ post, onClose, onDeleted, allowOwner = false }: Props) {
  const isAdmin = useAuthStore(s => s.user?.is_admin === true);
  const canManage = isAdmin || (allowOwner && post.is_mine);
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"menu" | "edit" | "delete">("menu");
  const [title, setTitle] = useState(post.title);
  const [content, setContent] = useState(post.content);
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: async (body: ManagePostBody | "delete") => {
      const currentUser = useAuthStore.getState().user;
      if (!currentUser || (!currentUser.is_admin && !(allowOwner && post.is_mine))) {
        throw new Error("게시글 관리 권한이 필요합니다.");
      }
      return body === "delete"
        ? deleteCommunityPost(post.slug)
        : currentUser.is_admin
          ? manageCommunityPost(post.slug, body)
          : updateCommunityPost(post.slug, {
            title: body.title,
            content: body.content,
          });
    },
    onSuccess: async (updated, body) => {
      await queryClient.cancelQueries({ queryKey: ["community", "posts"] });
      queryClient.setQueriesData<CommunityPost[]>({ queryKey: ["community", "posts"] }, previous => previous
        ? (body === "delete" ? previous.filter(item => item.id !== post.id) : previous.map(item => item.id === post.id && updated ? updated : item))
          .sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned) || new Date(b.created_at).getTime() - new Date(a.created_at).getTime() || b.id - a.id)
        : previous);
      if (updated) queryClient.setQueryData(["community", "post", post.slug, "admin"], updated);
      if (body === "delete") {
        queryClient.removeQueries({ queryKey: ["community", "post", post.slug] });
        onDeleted?.();
      }
      onClose();
      await queryClient.invalidateQueries({ queryKey: ["community"] });
    },
    onError: e => setError(getAxiosErrorMessage(e, "게시글 관리에 실패했습니다.")),
  });
  const close = () => { if (!mutation.isPending) onClose(); };
  const submit = () => {
    if (mutation.isPending) return;
    if (mode === "edit" && (!title.trim() || !content.trim())) { setError("제목과 내용을 입력해 주세요."); return; }
    mutation.mutate(mode === "delete" ? "delete" : { title: title.trim(), content: content.trim() });
  };
  if (!canManage) return null;
  const options = isAdmin
    ? [
      { label: "수정", Icon: Pencil, action: () => setMode("edit"), color: BRAND },
      { label: post.is_hidden ? "숨김 해제" : "숨김 처리", Icon: post.is_hidden ? Eye : EyeOff, action: () => mutation.mutate({ is_hidden: !post.is_hidden }), color: BRAND },
      { label: post.is_pinned ? "상단 고정 해제" : "상단 고정", Icon: post.is_pinned ? PinOff : Pin, action: () => mutation.mutate({ is_pinned: !post.is_pinned }), color: BRAND },
      { label: "삭제", Icon: Trash2, action: () => setMode("delete"), color: "#DC2626" },
    ]
    : [
      { label: "수정", Icon: Pencil, action: () => setMode("edit"), color: BRAND },
      { label: "삭제", Icon: Trash2, action: () => setMode("delete"), color: "#DC2626" },
    ];
  return (
    <Modal visible transparent animationType="fade" onRequestClose={close}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1, justifyContent: "center", paddingHorizontal: 20, paddingTop: insets.top + 20, paddingBottom: insets.bottom + 20 }}>
        <Pressable accessibilityLabel="닫기" onPress={close} style={{ position: "absolute", inset: 0, backgroundColor: "rgba(0,0,0,0.5)" }} />
        <View className="bg-white rounded-2xl p-6" style={{ maxHeight: "90%", width: "100%", maxWidth: 720, alignSelf: "center" }}>
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-bold text-gray-900">{mode === "menu" ? "게시글 관리" : mode === "edit" ? "게시글 수정" : "게시글 삭제"}</Text>
            <Pressable accessibilityLabel="닫기" disabled={mutation.isPending} onPress={close} className="p-2"><X size={22} color="#6B7280" /></Pressable>
          </View>
          <ScrollView keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag" style={{ flexShrink: 1 }}>
            {mode === "menu" ? <>
              <Text className="text-gray-500 mb-3" numberOfLines={2}>{post.title}</Text>
              {options.map(({ label, Icon, action, color }) => <Pressable key={label} disabled={mutation.isPending} onPress={action} className="flex-row items-center py-4 border-t border-gray-100"><Icon size={20} color={color} /><Text className="ml-3 text-base" style={{ color }}>{label}</Text></Pressable>)}
            </> : mode === "edit" ? <>
              <Text className="font-bold text-gray-700 mb-2">제목</Text>
              <TextInput accessibilityLabel="게시글 제목" editable={!mutation.isPending} value={title} onChangeText={setTitle} maxLength={255} className="border border-gray-200 rounded-xl px-4 py-3 text-gray-900 mb-4" />
              <Text className="font-bold text-gray-700 mb-2">내용</Text>
              <TextInput accessibilityLabel="게시글 내용" editable={!mutation.isPending} value={content} onChangeText={setContent} multiline textAlignVertical="top" className="border border-gray-200 rounded-xl p-4 text-gray-900" style={{ minHeight: 160 }} />
            </> : <Text className="text-gray-600">‘{post.title}’ 게시글과 연결된 댓글을 삭제하시겠습니까? 삭제 후 복구할 수 없습니다.</Text>}
            {!!error && <Text accessibilityRole="alert" className="text-red-600 mt-3">{error}</Text>}
            {mode !== "menu" && <Pressable disabled={mutation.isPending} onPress={submit} className="rounded-xl py-4 items-center mt-4" style={{ backgroundColor: mode === "delete" ? "#DC2626" : BRAND }}>{mutation.isPending ? <ActivityIndicator color="white" /> : <Text className="text-white font-bold">{mode === "delete" ? "삭제하기" : "저장하기"}</Text>}</Pressable>}
            {mode === "menu" && mutation.isPending && <ActivityIndicator color={BRAND} />}
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
