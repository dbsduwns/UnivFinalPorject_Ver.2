import { useQuery } from "@tanstack/react-query";

import { getCommunityPost, getCommunityPosts, getHotCommunityPosts } from "@/features/community/api/community";
import { useAuthStore } from "@/features/auth/store/auth-store";

export const communityQueryKeys = {
  all: ["community"] as const,
  posts: (boardSlug?: string, keyword?: string) =>
    [...communityQueryKeys.all, "posts", boardSlug ?? "all", keyword ?? ""] as const,
  post: (postSlug: string) => [...communityQueryKeys.all, "post", postSlug] as const,
};

export function useCommunityPosts(boardSlug?: string, keyword?: string, skip = 0) {
  const admin = useAuthStore(s => s.user?.is_admin === true);
  return useQuery({
    queryKey: [...communityQueryKeys.posts(boardSlug, keyword), admin ? "admin" : "user", skip],
    queryFn: () => getCommunityPosts({ boardSlug, keyword, skip }, admin),
    enabled: Boolean(boardSlug),
  });
}

export function useCommunityPost(postSlug?: string) {
  const admin = useAuthStore(s => s.user?.is_admin === true);
  return useQuery({
    queryKey: [...communityQueryKeys.post(postSlug ?? ""), admin ? "admin" : "user"],
    queryFn: () => getCommunityPost(postSlug!, admin),
    enabled: Boolean(postSlug),
  });
}

export function useHotCommunityPosts() {
  return useQuery({
    queryKey: [...communityQueryKeys.all, "hot"],
    queryFn: getHotCommunityPosts,
    staleTime: 30_000,
  });
}
