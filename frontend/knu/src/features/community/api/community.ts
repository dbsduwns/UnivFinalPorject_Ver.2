import { apiClient } from "@/api/client";

import type {
  CommentReport,
  CommunityComment,
  CommunityPost,
  CreateCommentBody,
  CreateCommentReportBody,
  CreatePostBody,
  CommunityImageAsset,
  GetPostsParams,
  LikeToggleResponse,
  UpdateCommentBody,
  UpdatePostBody,
  UserBlock,
} from "./types";

export const getCommunityPosts = async (
  params: GetPostsParams = {},
  admin = false,
): Promise<CommunityPost[]> => {
  const { data } = await apiClient.get<CommunityPost[]>(admin ? "/api/admin/community/posts" : "/api/community/", {
    params: {
      board_slug: params.boardSlug,
      keyword: params.keyword?.trim() || undefined,
      skip: params.skip ?? 0,
      limit: params.limit ?? 20,
    },
  });
  return data;
};

export const getCommunityPost = async (postSlug: string, admin = false): Promise<CommunityPost> => {
  const { data } = await apiClient.get<CommunityPost>(admin ? `/api/admin/community/posts/${encodeURIComponent(postSlug)}` : "/api/community/slug", {
    params: { post_slug: postSlug },
  });
  return data;
};

export const createCommunityPost = async (
  boardSlug: string,
  body: CreatePostBody,
  image?: CommunityImageAsset | null,
): Promise<CommunityPost> => {
  const formData = new FormData();
  formData.append("title", body.title);
  formData.append("content", body.content);
  formData.append("is_anonymous", String(Boolean(body.is_anonymous)));
  if (image) formData.append("image", image as unknown as Blob);
  const { data } = await apiClient.post<CommunityPost>("/api/community/posts", formData, {
    params: { board_slug: boardSlug },
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const updateCommunityPost = async (
  postSlug: string,
  body: UpdatePostBody
): Promise<CommunityPost> => {
  const { data } = await apiClient.put<CommunityPost>(
    `/api/community/${encodeURIComponent(postSlug)}`,
    body
  );
  return data;
};

export const deleteCommunityPost = async (postSlug: string): Promise<void> => {
  await apiClient.delete(`/api/community/${encodeURIComponent(postSlug)}`);
};

export const getComments = async (
  postId: number,
  parentCommentId?: number | null
): Promise<CommunityComment[]> => {
  const { data } = await apiClient.get<CommunityComment[]>("/api/community/comments", {
    params: {
      post_id: postId,
      parent_comment_id: parentCommentId ?? undefined,
    },
  });
  return data;
};

export const createComment = async (
  postId: number,
  body: CreateCommentBody
): Promise<CommunityComment> => {
  const { data } = await apiClient.post<CommunityComment>("/api/community/comments", body, {
    params: { post_id: postId },
  });
  return data;
};

export const updateComment = async (
  postId: number,
  commentId: number,
  body: UpdateCommentBody
): Promise<CommunityComment> => {
  const { data } = await apiClient.put<CommunityComment>(
    `/api/community/comments/${postId}/${commentId}`,
    body
  );
  return data;
};

export const deleteComment = async (postId: number, commentId: number): Promise<void> => {
  await apiClient.delete(`/api/community/comments/${postId}/${commentId}`);
};

export const reportComment = async (
  commentId: number,
  body: CreateCommentReportBody
): Promise<CommentReport> => {
  const { data } = await apiClient.post<CommentReport>(
    "/api/community/commentreports",
    body,
    { params: { comment_id: commentId } }
  );
  return data;
};

export const reportPost = async (
  postId: number,
  body: CreateCommentReportBody,
): Promise<CommentReport> => {
  const { data } = await apiClient.post<CommentReport>(
    "/api/community/postreports",
    body,
    { params: { post_id: postId } },
  );
  return data;
};

export const getMyCommentReports = async (): Promise<CommentReport[]> => {
  const { data } = await apiClient.get<CommentReport[]>('/api/community/my-comment-reports');
  return data;
};

export const getUserBlocks = async (): Promise<UserBlock[]> => {
  const { data } = await apiClient.get<UserBlock[]>('/api/community/userblocks');
  return data;
};

export const deleteUserBlock = async (blockId: number): Promise<{ message: string }> => {
  const { data } = await apiClient.delete<{ message: string }>(`/api/community/userblocks/${blockId}`);
  return data;
};

export const blockCommentAuthor = async (commentId: number): Promise<UserBlock> => {
  const { data } = await apiClient.post<UserBlock>(
    "/api/community/userblocks",
    undefined,
    { params: { comment_id: commentId } }
  );
  return data;
};

export const blockPostAuthor = async (postId: number): Promise<UserBlock> => {
  const { data } = await apiClient.post<UserBlock>(
    "/api/community/userblocks",
    undefined,
    { params: { post_id: postId } },
  );
  return data;
};

export const getPostLikeCount = async (postId: number): Promise<number> => {
  const { data } = await apiClient.get<number>(`/api/community/posts/${postId}/likes`);
  return data;
};

export const getIsPostLiked = async (postId: number): Promise<boolean> => {
  const { data } = await apiClient.get<boolean>(`/api/community/posts/${postId}/likes/me`);
  return data;
};

export const togglePostLike = async (postId: number): Promise<LikeToggleResponse> => {
  const { data } = await apiClient.put<LikeToggleResponse>(
    `/api/community/posts/${postId}/likes`
  );
  return data;
};

const commentLikePath = (postId: number, commentId: number) =>
  `/api/community/posts/${postId}/comments/${commentId}/likes`;

export const getCommentLikeCount = async (
  postId: number,
  commentId: number
): Promise<number> => {
  const { data } = await apiClient.get<number>(commentLikePath(postId, commentId));
  return data;
};

export const getIsCommentLiked = async (
  postId: number,
  commentId: number
): Promise<boolean> => {
  const { data } = await apiClient.get<boolean>(`${commentLikePath(postId, commentId)}/me`);
  return data;
};

export const toggleCommentLike = async (
  postId: number,
  commentId: number
): Promise<LikeToggleResponse> => {
  const { data } = await apiClient.put<LikeToggleResponse>(commentLikePath(postId, commentId));
  return data;
};
