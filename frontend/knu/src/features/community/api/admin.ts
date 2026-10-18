import { apiClient } from "@/api/client";
import type { CommentReport, CommunityPost } from "./types";

export type AdminReport = CommentReport & {
  reporter_id: number | null;
  reported_user_id: number | null;
  content_snapshot: string;
  reviewed_by_id: number | null;
  resolution_note: string | null;
  report_count: number;
  pending_report_count: number;
  post_id: number | null;
  comment_is_hidden: boolean | null;
};
export type AdminBlock = { id: number; blocker_id: number; blocked_user_id: number; created_at: string };
export const getAdminReports = async (skip: number) =>
  (await apiClient.get<AdminReport[]>("/api/admin/comment-reports", { params: { skip, limit: 20 } })).data;
export const getAdminBlocks = async (skip: number) =>
  (await apiClient.get<AdminBlock[]>("/api/admin/user-blocks", { params: { skip, limit: 20 } })).data;
export const reviewReport = async (id: number, status: Exclude<CommentReport["status"], "pending">, resolution_note: string) =>
  (await apiClient.patch<AdminReport>(`/api/admin/comment-reports/${id}`, { status, resolution_note: resolution_note.trim() || null })).data;

export type ManagePostBody = Partial<Pick<CommunityPost, "title" | "content" | "is_hidden" | "is_pinned">>;
export const manageCommunityPost = async (slug: string, body: ManagePostBody) =>
  (await apiClient.patch<CommunityPost>(`/api/admin/community/posts/${encodeURIComponent(slug)}`, body)).data;
export const moderateReportedComment = async (postId: number, commentId: number, hidden: boolean, reason: string) =>
  (await apiClient.patch(`/api/admin/community/comments/${postId}/${commentId}/moderation`, { action: hidden ? "hide" : "restore", reason: reason.trim() || null })).data;
