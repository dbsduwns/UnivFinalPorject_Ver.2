export type CommunityPost = {
  id: number;
  slug: string;
  board_slug: string;
  title: string;
  content: string;
  author_name: string;
  is_anonymous: boolean;
  created_at: string;
  updated_at: string;
};

export type CreatePostBody = {
  title: string;
  content: string;
  is_anonymous?: boolean;
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
