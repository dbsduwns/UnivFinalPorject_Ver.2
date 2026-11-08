import { useState } from "react";
import { Redirect, router } from "expo-router";
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { ChevronLeft, Flag, ShieldCheck, UserRoundX, X } from "lucide-react-native";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { getAxiosErrorMessage } from "@/api/errors";
import { getAdminBlocks, getAdminReports, reviewReport, type AdminReport } from "@/features/community/api/admin";
import type { CommentReportReason } from "@/features/community/api/types";
import { ReportCommentActions } from "@/features/community/components/ReportCommentActions";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout"

const BRAND = "#13708D";
const STATUSES = { pending: "접수", reviewing: "검토 중", resolved: "처리 완료", dismissed: "기각" };
const REASONS: Record<CommentReportReason, string> = { abuse: "욕설·비방", hate: "혐오·차별", sexual: "음란성", spam: "광고·도배", personal_info: "개인정보 노출", impersonation: "사칭", illegal: "불법 정보", other: "기타" };
const date = (value: string) => new Date(value).toLocaleString("ko-KR");

export default function CommunityAdminScreen() {
  
  const insets = useSafeAreaInsets();

  const ready = useAuthStore(s => s.ready);
  const user = useAuthStore(s => s.user);
  const allowed = ready && user?.is_admin === true;
  
  const [tab, setTab] = useState<"reports" | "blocks">("reports");
  const [selected, setSelected] = useState<AdminReport | null>(null);
  
  const reports = useInfiniteQuery({
    queryKey: ["community-admin", "reports"], 
    queryFn: ({ pageParam }) => getAdminReports(pageParam), 
    initialPageParam: 0,
    getNextPageParam: (last, pages) => last.length === 20 ? pages.length * 20 : undefined, 
    enabled: allowed && tab === "reports",
  });
  const blocks = useInfiniteQuery({ 
    queryKey: ["community-admin", "blocks"], 
    queryFn: ({ pageParam }) => getAdminBlocks(pageParam), initialPageParam: 0, 
    getNextPageParam: (last, pages) => last.length === 20 ? pages.length * 20 : undefined, 
    enabled: allowed && tab === "blocks" 
  });

  {/* 로그인 */}
  if (!ready) 
    return <View className="flex-1 items-center justify-center"><ActivityIndicator color={BRAND} /></View>;
  
  {/* 유저 인증 */}
  if (!user) 
    return <Redirect href="/(auth)/login" />;
  
  {/* 관리자 인증 */}
  if (!user.is_admin) 
    return <Redirect href="/(app)/(tabs)/community" />;

  const active = tab === "reports" ? reports : blocks;
  const empty = <View className="py-16 items-center px-5">
                  {active.isPending ? <ActivityIndicator color={BRAND} /> : active.isError ? 
                    <>
                      <Text className="text-gray-500 text-center">{getAxiosErrorMessage(active.error, "내역을 불러오지 못했습니다.")}</Text>
                      <Pressable onPress={() => void active.refetch()} className="p-4">
                        <Text style={{ color: BRAND }}>다시 시도</Text>
                      </Pressable>
                    </> : <Text className="text-gray-400">{tab === "reports" ? "접수된 댓글 신고가 없습니다." : "사용자 간 차단 내역이 없습니다."}</Text>
                  }
                </View>;
  const footer =  <View className="items-center py-5">
                    {active.isFetchNextPageError && <Text className="text-red-600 mb-2">추가 내역을 불러오지 못했습니다.</Text>}
                    {active.hasNextPage &&  <Pressable 
                                              disabled={active.isFetching} 
                                              onPress={() => void active.fetchNextPage()} 
                                              className="px-6 py-3 rounded-xl bg-white border border-gray-200"
                                            >
                                              {active.isFetchingNextPage ? <ActivityIndicator color={BRAND} /> : <Text style={{ color: BRAND }}>더 보기</Text>}
                                            </Pressable>
                      }
                  </View>;
  
  return (
    <AppScreenLayout>
      <View className="bg-[#F4F6F8]">
        <View className="bg-white px-5 py-4 border-b border-gray-200">
          <View className="flex-row items-center">
            <Pressable 
              accessibilityLabel="뒤로 가기" 
              onPress={() => router.canGoBack() ? router.back() : router.replace("/(app)/(tabs)/community")}
              className="p-2 -ml-2"
            >
              <ChevronLeft size={26} color="#374151" />
            </Pressable>
            <Text className="flex-1 ml-2 text-xl font-extrabold text-gray-900">신고·차단 관리</Text>
            <ShieldCheck size={20} color={BRAND} />
            <Text className="ml-1 text-xs font-bold text-[#13708D]">관리자</Text>
          </View>
          <View className="flex-row mt-4">
            {(["reports", "blocks"] as const)
              .map(value => 
                  <Pressable 
                    accessibilityRole="tab" 
                    accessibilityState={{ selected: tab === value }} 
                    key={value} 
                    onPress={() => setTab(value)} 
                    className="flex-1 flex-row justify-center items-center rounded-xl py-3" 
                    style={{ backgroundColor: tab === value ? "#E8F3F6" : "#F9FAFB", marginRight: value === "reports" ? 8 : 0 }}
                  >
                    {value === "reports" ? <Flag size={17} color={BRAND} /> : <UserRoundX size={17} color={BRAND} />}
                    <Text className="ml-2 font-bold text-[#13708D]">
                      {value === "reports" ? "댓글 신고" : "차단 내역"}
                    </Text>
                  </Pressable>
                    )
              }
          </View>
        </View>
        {tab === "reports" ? 
          <FlatList 
            key="reports" 
            data={reports.data?.pages.flat() ?? []} 
            keyExtractor={item => String(item.id)} 
            contentContainerStyle={{ padding: 20, paddingBottom: insets.bottom + 20 }} 
            refreshing={reports.isRefetching && !reports.isFetchingNextPage} 
            onRefresh={() => void reports.refetch()} 
            ListEmptyComponent={empty} 
            ListFooterComponent={footer} 
            renderItem={({ item }) => <Pressable accessibilityRole="button" onPress={() => setSelected(item)} className="bg-white rounded-2xl border border-gray-200 p-5 mb-3">
                                        <View className="flex-row items-center justify-between">
                                          <Text className="font-bold text-gray-900">{REASONS[item.reason]}</Text>
                                          <Text className="text-xs font-bold text-[#13708D] bg-cyan-50 px-3 py-1 rounded-full">{STATUSES[item.status]}</Text>
                                        </View>
                                        <Text className="text-gray-700 mt-3" numberOfLines={3}>{item.content_snapshot}</Text>
                                        <Text className="text-xs font-bold text-[#13708D] mt-3">누적 {item.report_count}건 · 미처리 {item.pending_report_count}건</Text>
                                        <Text className="text-xs text-gray-400 mt-3">{item.post_id != null ? "게시글 신고" : "댓글 신고"} #{item.id} · {date(item.created_at)}</Text></Pressable>} />
        : <FlatList
            key="blocks" 
            data={blocks.data?.pages.flat() ?? []} 
            keyExtractor={item => String(item.id)} 
            contentContainerStyle={{ padding: 20, paddingBottom: insets.bottom + 20 }} 
            refreshing={blocks.isRefetching && !blocks.isFetchingNextPage} 
            onRefresh={() => void blocks.refetch()} 
            ListHeaderComponent={
              <Text className="text-xs text-gray-500 mb-4">사용자가 설정한 개인 차단 내역입니다. 서비스 이용 정지와는 별개입니다.</Text>
            } 
            ListEmptyComponent={empty} 
            ListFooterComponent={footer} 
            renderItem={({ item }) => <View className="bg-white rounded-2xl border border-gray-200 p-5 mb-3">
                                        <Text className="font-bold text-gray-900">사용자 #{item.blocker_id} → 사용자 #{item.blocked_user_id}</Text>
                                        <Text className="text-sm text-gray-500 mt-2">개인 차단 · 내역 #{item.id}</Text>
                                        <Text className="text-xs text-gray-400 mt-2">{date(item.created_at)}</Text>
                                      </View>
                          } 
            />
          }
          {selected && <ReportReview key={selected.id} report={selected} onClose={() => setSelected(null)} />}
      </View>
    </AppScreenLayout>
  )
}

function ReportReview({ report, onClose }: { report: AdminReport; onClose: () => void }) {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<"reviewing" | "resolved" | "dismissed">(report.status === "pending" ? "reviewing" : report.status);
  const [note, setNote] = useState(report.resolution_note ?? "");
  const [error, setError] = useState("");
  const mutation = useMutation({ mutationFn: () => reviewReport(report.id, status, note), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["community-admin", "reports"] }); onClose(); }, onError: e => setError(getAxiosErrorMessage(e, "신고 처리에 실패했습니다.")) });
  const close = () => { if (!mutation.isPending) onClose(); };
  const submit = () => { if (mutation.isPending) return; if (status !== "reviewing" && !note.trim()) { setError("처리 완료 또는 기각 시 처리 메모를 입력해 주세요."); return; } setError(""); mutation.mutate(); };
  return (
    <Modal 
      transparent 
      visible 
      animationType="fade" 
      onRequestClose={close}
    >
      <KeyboardAvoidingView 
        behavior={Platform.OS === "ios" ? "padding" : "height"} 
        keyboardVerticalOffset={0} 
        style={{ flex: 1, justifyContent: "center", paddingHorizontal: 20, paddingTop: insets.top + 20, paddingBottom: insets.bottom + 20 }}
      >
        <Pressable accessibilityLabel="닫기" onPress={close} style={{ position: "absolute", inset: 0, backgroundColor: "rgba(0,0,0,0.5)" }} />
          <View className="bg-white rounded-2xl p-6" style={{ maxHeight: "90%", width: "100%", maxWidth: 720, alignSelf: "center" }}>
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-lg font-bold text-gray-900">{report.post_id != null ? "게시글" : "댓글"} 신고 #{report.id}</Text>
              <Pressable disabled={mutation.isPending} accessibilityLabel="닫기" onPress={close} className="p-2"><X size={22} color="#6B7280" /></Pressable>
            </View>
          <ScrollView 
            keyboardShouldPersistTaps="handled" 
            keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} 
            style={{ flexShrink: 1 }} 
            contentContainerStyle={{ paddingBottom: 8 }}
          >
            <Text className="font-bold text-[#13708D]">{REASONS[report.reason]} · {STATUSES[report.status]}</Text>
            <Text className="text-xs text-gray-500 mt-2">신고자 #{report.reporter_id ?? "삭제됨"} · 대상 #{report.reported_user_id ?? "삭제됨"}</Text>
            <Text className="text-xs text-gray-400 mt-1">{date(report.created_at)}</Text>
            <Text className="bg-gray-50 rounded-xl p-4 text-gray-800 my-4">{report.content_snapshot}</Text>
            {!!report.description && <Text className="text-gray-600 mb-4">신고 설명: {report.description}</Text>}
            <Text className="text-xs text-gray-500 mb-4">신고 당시 {report.post_id != null ? "게시글" : "댓글"} 내용입니다. 처리 상태 변경만으로 원본이 삭제되거나 사용자가 정지되지는 않습니다.</Text>
            {report.reviewed_at && <Text className="text-xs text-gray-400 mb-3">최근 처리: {date(report.reviewed_at)} · 관리자 #{report.reviewed_by_id ?? "삭제됨"}</Text>}
            <View className="flex-row mb-4">
              {(["reviewing", "resolved", "dismissed"] as const)
              .map(value => 
                <Pressable 
                  key={value} 
                  disabled={mutation.isPending} 
                  onPress={() => setStatus(value)} 
                  className="flex-1 py-3 mr-1 rounded-xl items-center"
                  style={{ backgroundColor: status === value ? "#E8F3F6" : "#F3F4F6" }}
                >
                  <Text style={{ color: status === value ? BRAND : "#6B7280", fontWeight: "700" }}>
                    {STATUSES[value]}
                  </Text>
                </Pressable>
              )}
              </View>
              {report.comment_id != null && <ReportCommentActions report={report} note={note} />}
              <TextInput 
                accessibilityLabel="신고 처리 메모" 
                editable={!mutation.isPending} 
                multiline 
                textAlignVertical="top" 
                maxLength={1000} 
                value={note} 
                onChangeText={setNote} 
                placeholder="처리 메모 (완료·기각 시 필수)" 
                className="border border-gray-200 rounded-xl p-4 text-gray-800" 
                style={{ minHeight: 100 }}
              />{!!error && <Text accessibilityRole="alert" className="text-red-600 mt-3">{error}</Text>}
            <Pressable 
              disabled={mutation.isPending} 
              onPress={submit} 
              className="bg-[#13708D] rounded-xl py-4 items-center mt-4"
            >
              {mutation.isPending ? <ActivityIndicator color="white" /> : <Text className="font-bold text-white">처리 상태 저장</Text>}
            </Pressable>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  )
}
