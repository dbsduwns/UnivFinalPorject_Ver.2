import { useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { Flag, UserRoundX, X } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import { blockPostAuthor, reportPost } from "@/features/community/api/community";
import type { CommentReportReason, CommunityPost } from "@/features/community/api/types";

const REPORT_REASONS: readonly { value: CommentReportReason; label: string }[] = [
  { value: "abuse", label: "욕설 및 괴롭힘" },
  { value: "hate", label: "혐오 표현" },
  { value: "sexual", label: "성적 콘텐츠" },
  { value: "spam", label: "스팸 및 도배" },
  { value: "personal_info", label: "개인정보 노출" },
  { value: "impersonation", label: "사칭" },
  { value: "illegal", label: "불법 콘텐츠" },
  { value: "other", label: "기타" },
];

export function PostUserActionsModal({ post, onClose }: { post: CommunityPost; onClose: () => void }) {
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<"menu" | "report">("menu");
  const [reason, setReason] = useState<CommentReportReason>("abuse");
  const [description, setDescription] = useState("");
  const reportMutation = useMutation({
    mutationFn: () => reportPost(post.id, { reason, description: description.trim() || null }),
    onSuccess: () => {
      Alert.alert("신고 접수 완료", "게시글 신고가 접수되었습니다.");
      onClose();
    },
    onError: (error) => Alert.alert("신고 실패", getAxiosErrorMessage(error)),
  });
  const blockMutation = useMutation({
    mutationFn: () => blockPostAuthor(post.id),
    onSuccess: () => {
      Alert.alert("차단 완료", "작성자의 게시글과 댓글이 더 이상 표시되지 않습니다.");
      onClose();
    },
    onError: (error) => Alert.alert("작성자 차단 실패", getAxiosErrorMessage(error)),
  });
  const pending = reportMutation.isPending || blockMutation.isPending;

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView className="flex-1 bg-black/40 justify-end" behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View className="bg-white rounded-t-3xl px-5 pt-5" style={{ paddingBottom: Math.max(insets.bottom, 16), maxHeight: "88%" }}>
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-lg font-extrabold text-gray-900">{mode === "menu" ? "게시글 메뉴" : "게시글 신고"}</Text>
            <Pressable accessibilityLabel="닫기" disabled={pending} onPress={onClose} className="w-9 h-9 rounded-full bg-gray-100 items-center justify-center">
              <X size={18} color="#475569" />
            </Pressable>
          </View>
          {mode === "menu" ? (
            <>
              <Pressable disabled={pending} onPress={() => setMode("report")} className="h-14 flex-row items-center border-b border-gray-100">
                <Flag size={19} color="#475569" />
                <Text className="ml-3 text-base font-bold text-gray-800">신고</Text>
              </Pressable>
              <Pressable disabled={pending} onPress={() => Alert.alert("작성자 차단", "이 작성자를 차단할까요?", [
                { text: "취소", style: "cancel" },
                { text: "차단", style: "destructive", onPress: () => blockMutation.mutate() },
              ])} className="h-14 flex-row items-center">
                <UserRoundX size={19} color="#DC2626" />
                <Text className="ml-3 text-base font-bold text-red-500">작성자 차단</Text>
              </Pressable>
            </>
          ) : (
            <ScrollView keyboardShouldPersistTaps="handled">
              <Text className="text-sm font-bold text-gray-700 mb-2">신고 사유</Text>
              {REPORT_REASONS.map((item) => (
                <Pressable key={item.value} onPress={() => setReason(item.value)} className={`h-12 px-4 mb-2 rounded-2xl flex-row items-center justify-between ${reason === item.value ? "bg-cyan-50 border border-[#13708D]" : "bg-gray-100"}`}>
                  <Text className={`text-sm font-bold ${reason === item.value ? "text-[#13708D]" : "text-gray-600"}`}>{item.label}</Text>
                  <View className={`w-5 h-5 rounded-full border-2 items-center justify-center ${reason === item.value ? "border-[#13708D]" : "border-gray-300"}`}>
                    {reason === item.value ? <View className="w-2.5 h-2.5 rounded-full bg-[#13708D]" /> : null}
                  </View>
                </Pressable>
              ))}
              <Text className="text-sm font-bold text-gray-700 mt-2 mb-2">상세 내용 {reason === "other" ? "(필수)" : "(선택)"}</Text>
              <TextInput value={description} onChangeText={setDescription} placeholder="신고 내용을 입력해주세요" placeholderTextColor="#94A3B8" multiline maxLength={1000} textAlignVertical="top" className="min-h-24 max-h-36 rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-900" />
              <Pressable onPress={() => reportMutation.mutate()} disabled={pending || (reason === "other" && !description.trim())} className="h-12 mt-4 rounded-2xl bg-[#13708D] items-center justify-center disabled:opacity-40">
                {reportMutation.isPending ? <ActivityIndicator color="white" size="small" /> : <Text className="text-sm font-extrabold text-white">신고하기</Text>}
              </Pressable>
            </ScrollView>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
