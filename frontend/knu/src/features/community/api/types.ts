export type CommunityPost = {
  id: number;
  slug: string;
  board_slug: string;
  title: string;
  content: string;
  image_url: string | null;
  author_name: string;
  is_anonymous: boolean;
  is_hidden: boolean;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  is_mine: boolean;
};

export type HotCommunityPost = CommunityPost & {
  like_count: number;
  comment_count: number;
  hot_score: number;
};

export type CreatePostBody = {
  title: string;
  content: string;
  is_anonymous?: boolean;
};

export type CommunityImageAsset = {
  uri: string;
  name: string;
  type: string;
};

export type UpdatePostBody = Partial<CreatePostBody>;

export type CommunityComment = {
  id: number;
  content: string;
  post_id: number;
  author_name: string;
  parent_comment_id: number | null;
  is_anonymous: boolean;
  commented_at: string;
  updated_at: string;
  is_mine: boolean;
};

export type CreateCommentBody = {
  content: string;
  parent_comment_id?: number | null;
  is_anonymous?: boolean;
};

export type UpdateCommentBody = {
  content?: string;
  is_anonymous?: boolean;
};

export type CommentReportReason =
  | "abuse"
  | "hate"
  | "sexual"
  | "spam"
  | "personal_info"
  | "impersonation"
  | "illegal"
  | "other";

export type CreateCommentReportBody = {
  reason: CommentReportReason;
  description?: string | null;
};

export type CommentReport = {
  id: number;
  comment_id: number | null;
  post_id: number | null;
  reason: CommentReportReason;
  description: string | null;
  content_snapshot: string;
  status: "pending" | "reviewing" | "resolved" | "dismissed";
  resolution_note: string | null;
  created_at: string;
  reviewed_at: string | null;
};

export type UserBlock = {
  id: number;
  created_at: string;
  blocked_user_id?: number;
  display_name?: string;
};

export type LikeToggleResponse = {
  liked: boolean;
  like_count: number;
};

export type GetPostsParams = {
  boardSlug?: string;
  keyword?: string;
  skip?: number;
  limit?: number;
};
