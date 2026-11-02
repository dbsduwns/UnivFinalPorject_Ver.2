import { useQuery } from "@tanstack/react-query";

import { chatApi } from "@/features/chat/api/chat-api";
import { useAuthStore } from "@/features/auth/store/auth-store";

export function useUnreadChatCount() {
  const userId = useAuthStore((state) => state.user?.id);
  const { data: rooms } = useQuery({
    queryKey: ["chatRooms", userId],
    queryFn: async () => (await chatApi.getRooms()).data,
    enabled: !!userId,
    refetchInterval: 10_000,
  });

  return userId ? rooms?.reduce((total, room) => total + room.unread_count, 0) ?? 0 : 0;
}
