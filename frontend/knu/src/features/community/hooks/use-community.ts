import { useQuery } from "@tanstack/react-query";

import { getCommunityPost, getCommunityPosts } from "@/features/community/api/community";

export const communityQueryKeys = {
  all: ["community"] as const,
  posts: (boardSlug?: string, keyword?: string) =>
    [...communityQueryKeys.all, "posts", boardSlug ?? "all", keyword ?? ""] as const,
  post: (postSlug: string) => [...communityQueryKeys.all, "post", postSlug] as const,
};

export function useCommunityPosts(boardSlug?: string, keyword?: string) {
  return useQuery({
    queryKey: communityQueryKeys.posts(boardSlug, keyword),
    queryFn: () => getCommunityPosts({ boardSlug, keyword }),
    enabled: Boolean(boardSlug),
  });
}

export function useCommunityPost(postSlug?: string) {
  return useQuery({
    queryKey: communityQueryKeys.post(postSlug ?? ""),
    queryFn: () => getCommunityPost(postSlug!),
    enabled: Boolean(postSlug),
  });
}
