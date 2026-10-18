import { useQuery } from "@tanstack/react-query";
import { getNotice, getNotices } from "@/features/notice/api/notice";

export const useNotices = (keyword = "") => {
    const search = keyword.trim();
    return useQuery({
        queryKey: ["notices", search],
        queryFn: () => getNotices(search),
        select: (notices) => [...notices].sort((a, b) => {
            if (a.is_important !== b.is_important) return Number(b.is_important) - Number(a.is_important);
            const timeA = new Date(a.published_at ?? a.crawled_at ?? 0).getTime();

            const timeB = new Date(b.published_at ?? b.crawled_at ?? 0).getTime();

            return timeB - timeA || b.id - a.id;
        }),
    });
};

export const useNotice = (id: number | null) => {
    return useQuery({
        queryKey: ["notice", id],
        queryFn: () => getNotice(id!),
        enabled: !!id,
    })
}
