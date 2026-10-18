import { useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { Eye, EyeOff, Trash2 } from "lucide-react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { getAxiosErrorMessage } from "@/api/errors";
import { moderateReportedComment, type AdminReport } from "@/features/community/api/admin";
import { deleteComment } from "@/features/community/api/community";

export function ReportCommentActions({ report, note }: { report: AdminReport; note: string }) {
  const client = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const detail = useQuery({ queryKey: ["community-admin", "reports", report.id], queryFn: async () => (await apiClient.get<AdminReport>(`/api/admin/comment-reports/${report.id}`)).data, initialData: report });
  const current = detail.data;
  const mutation = useMutation({
    mutationFn: async (action: "visibility" | "delete") => {
      if (current.post_id == null || current.comment_id == null) throw new Error("삭제된 댓글입니다.");
      return action === "delete"
        ? deleteComment(current.post_id, current.comment_id)
        : moderateReportedComment(current.post_id, current.comment_id, !current.comment_is_hidden, note.slice(0, 500));
    },
    onSuccess: async () => {
      setConfirmDelete(false);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["community-admin", "reports"] }),
        client.invalidateQueries({ queryKey: ["community"] }),
      ]);
    },
    onError: e => setError(getAxiosErrorMessage(e, "댓글 관리에 실패했습니다.")),
  });
  const run = (action: "visibility" | "delete") => { if (mutation.isPending) return; setError(""); mutation.mutate(action); };
  const deleted = current.comment_id == null || current.post_id == null;
  return <View className="border border-gray-200 rounded-xl p-4 mb-4">
    <Text className="font-bold text-gray-800">누적 신고 {current.report_count}건 · 미처리 {current.pending_report_count}건</Text>
    <Text className="text-xs text-gray-500 mt-2">{deleted ? "원본 댓글이 삭제되었습니다. 신고 기록은 유지됩니다." : current.comment_is_hidden ? "현재 숨김 처리된 댓글입니다." : "현재 공개 중인 댓글입니다."}</Text>
    {!deleted && <View className="flex-row mt-3">
      <Pressable disabled={mutation.isPending} onPress={() => run("visibility")} className="flex-1 flex-row items-center justify-center bg-cyan-50 rounded-xl py-3 mr-2">{current.comment_is_hidden ? <Eye size={16} color="#13708D" /> : <EyeOff size={16} color="#13708D" />}<Text className="ml-2 font-bold text-[#13708D]">{current.comment_is_hidden ? "숨김 해제" : "댓글 숨김"}</Text></Pressable>
      <Pressable disabled={mutation.isPending} onPress={() => setConfirmDelete(true)} className="flex-row items-center bg-red-50 rounded-xl px-3"><Trash2 size={16} color="#DC2626" /><Text className="ml-1 font-bold text-red-600">삭제</Text></Pressable>
    </View>}
    {confirmDelete && !deleted && <View className="mt-3"><Text className="text-sm text-gray-600">댓글과 답글이 삭제되며 복구할 수 없습니다.</Text><View className="flex-row mt-2"><Pressable disabled={mutation.isPending} onPress={() => setConfirmDelete(false)} className="flex-1 p-3 items-center"><Text className="text-gray-600">취소</Text></Pressable><Pressable disabled={mutation.isPending} onPress={() => run("delete")} className="flex-1 p-3 items-center rounded-xl bg-red-600"><Text className="font-bold text-white">삭제 확인</Text></Pressable></View></View>}
    {mutation.isPending && <ActivityIndicator color="#13708D" style={{ marginTop: 12 }} />}
    {!!error && <Text className="text-red-600 mt-2">{error}</Text>}
  </View>;
}
