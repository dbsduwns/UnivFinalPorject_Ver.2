import { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Switch, Text, TextInput, View } from "react-native";
import { Pencil, Pin, PinOff, ShieldCheck, Trash2, X } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { getAxiosErrorMessage } from "@/api/errors";
import { createNotice, deleteNotice, updateNotice, type NoticeInput } from "@/features/notice/api/notice";
import type { Notice } from "@/features/notice/types";
import { useAuthStore } from "@/features/auth/store/auth-store";

const COLOR = "#13708D";
export const NOTICE_CATEGORIES = ["학사", "장학", "학습/상담", "취창업"];

export function AdminBadge() {
  return <View className="flex-row items-center self-start rounded-full px-3 py-1.5 bg-[#E8F3F6]"><ShieldCheck size={14} color={COLOR} /><Text className="ml-1 text-xs font-bold text-[#13708D]">관리자</Text></View>;
}

type Props = { notice: Notice | null; creating: boolean; onClose: () => void; onPinned?: () => void };

export function NoticeAdmin({ notice, creating, onClose, onPinned }: Props) {
  const isAdmin = useAuthStore(s => s.user?.is_admin);
  const [editing, setEditing] = useState(creating);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [title, setTitle] = useState(notice?.title ?? "");
  const [content, setContent] = useState(notice?.content ?? "");
  const [category, setCategory] = useState(notice?.category ?? "학사");
  const [important, setImportant] = useState(notice?.is_important ?? false);
  const [error, setError] = useState("");
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (action: "save" | "pin" | "delete") => {
      if (!useAuthStore.getState().user?.is_admin) throw new Error("관리자 권한이 필요합니다.");
      if (action === "delete" && notice) return deleteNotice(notice.id);
      if (action === "pin" && notice) return updateNotice(notice.id, { is_important: !notice.is_important });
      const body: NoticeInput = { title: title.trim(), content: content.trim(), category, is_important: important };
      return notice ? updateNotice(notice.id, body) : createNotice(body);
    },
    onSuccess: async (updated, action) => {
      // 저장된 서버 값을 먼저 반영해 목록과 다음 관리 메뉴가 같은 상태를 사용한다.
      await queryClient.cancelQueries({ queryKey: ["notices"] });
      queryClient.setQueriesData<Notice[]>({ queryKey: ["notices"] }, previous => {
        if (!previous || !notice) return previous;
        return action === "delete"
          ? previous.filter(item => item.id !== notice.id)
          : previous.map(item => item.id === notice.id && updated ? updated : item);
      });
      if (updated) queryClient.setQueryData(["notice", updated.id], updated);
      await queryClient.invalidateQueries({ queryKey: ["notices"] });
      if (notice) {
        if (action === "delete") queryClient.removeQueries({ queryKey: ["notice", notice.id] });
        else await queryClient.invalidateQueries({ queryKey: ["notice", notice.id] });
      }
      if (updated?.is_important) onPinned?.();
      onClose();
    },
    onError: e => setError(getAxiosErrorMessage(e, "처리하지 못했습니다. 다시 시도해 주세요.")),
  });
  if (!isAdmin) return null;
  const close = () => { if (!mutation.isPending) onClose(); };
  const run = (action: "save" | "pin" | "delete") => {
    if (mutation.isPending) return;
    setError("");
    if (action === "save" && (!title.trim() || !content.trim())) {
      setError("제목과 내용을 입력해 주세요.");
      return;
    }
    mutation.mutate(action);
  };
  return (
    <Modal visible transparent animationType="slide" onRequestClose={close}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, justifyContent: "flex-end" }}>
        <Pressable accessibilityLabel="닫기" onPress={close} style={{ position: "absolute", inset: 0, backgroundColor: "rgba(0,0,0,0.35)" }} />
        <View className="bg-white rounded-t-3xl px-5 pt-5" style={{ maxHeight: "90%", width: "100%", maxWidth: 720, alignSelf: "center", paddingBottom: Math.max(insets.bottom, 20) }}>
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-bold text-gray-900">{confirmDelete ? "공지 삭제" : editing ? (creating ? "공지 등록" : "공지 수정") : "공지 관리"}</Text>
            <Pressable accessibilityLabel="닫기" disabled={mutation.isPending} onPress={close} className="p-2"><X size={22} color="#6B7280" /></Pressable>
          </View>
          <ScrollView keyboardShouldPersistTaps="handled">
            {confirmDelete ? <Text className="text-base text-gray-600 mb-5">‘{notice?.title}’ 공지를 삭제하시겠습니까? 삭제한 공지는 복구할 수 없습니다.</Text> : editing ? <>
              <Text className="text-sm font-bold text-gray-700 mb-2">분류</Text>
              <View className="flex-row flex-wrap mb-4">{Array.from(new Set([...NOTICE_CATEGORIES, category])).map(c => <Pressable key={c} disabled={mutation.isPending} onPress={() => setCategory(c)} className="px-3 py-2 mr-2 mb-2 rounded-full border" style={{ backgroundColor: c === category ? "#E8F3F6" : "#F9FAFB", borderColor: c === category ? COLOR : "#E5E7EB" }}><Text style={{ color: c === category ? COLOR : "#4B5563" }}>{c}</Text></Pressable>)}</View>
              <Text className="text-sm font-bold text-gray-700 mb-2">제목</Text>
              <TextInput accessibilityLabel="공지 제목" editable={!mutation.isPending} value={title} onChangeText={setTitle} maxLength={300} placeholder="제목을 입력해 주세요" className="border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 mb-4" />
              <Text className="text-sm font-bold text-gray-700 mb-2">내용</Text>
              <TextInput accessibilityLabel="공지 내용" editable={!mutation.isPending} value={content} onChangeText={setContent} multiline textAlignVertical="top" placeholder="내용을 입력해 주세요" className="border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900" style={{ minHeight: 180 }} />
              <View className="flex-row items-center justify-between py-4"><Text className="text-sm text-gray-700">상단 고정</Text><Switch accessibilityLabel="상단 고정" disabled={mutation.isPending} value={important} onValueChange={setImportant} trackColor={{ true: COLOR }} /></View>
            </> : <>
              <Text numberOfLines={2} className="text-gray-500 mb-4">{notice?.title}</Text>
              <Pressable disabled={mutation.isPending} onPress={() => setEditing(true)} className="flex-row items-center py-4"><Pencil size={20} color={COLOR} /><Text className="ml-3 text-base text-gray-800">수정</Text></Pressable>
              <Pressable disabled={mutation.isPending} onPress={() => run("pin")} className="flex-row items-center py-4 border-t border-gray-100">{notice?.is_important ? <PinOff size={20} color={COLOR} /> : <Pin size={20} color={COLOR} />}<Text className="ml-3 text-base text-gray-800">{notice?.is_important ? "상단 고정 해제" : "상단 고정"}</Text></Pressable>
              <Pressable disabled={mutation.isPending} onPress={() => setConfirmDelete(true)} className="flex-row items-center py-4 border-t border-gray-100"><Trash2 size={20} color="#DC2626" /><Text className="ml-3 text-base text-red-600">삭제</Text></Pressable>
            </>}
            {!!error && <Text accessibilityRole="alert" className="text-red-600 my-3">{error}</Text>}
            {(editing || confirmDelete) && <Pressable disabled={mutation.isPending} onPress={() => run(confirmDelete ? "delete" : "save")} className="rounded-xl py-4 items-center mt-2" style={{ backgroundColor: confirmDelete ? "#DC2626" : COLOR, opacity: mutation.isPending ? 0.5 : 1 }}>{mutation.isPending ? <ActivityIndicator color="white" /> : <Text className="text-white font-bold">{confirmDelete ? "삭제하기" : creating ? "등록하기" : "저장하기"}</Text>}</Pressable>}
            {mutation.isPending && !editing && !confirmDelete && <ActivityIndicator color={COLOR} />}
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
