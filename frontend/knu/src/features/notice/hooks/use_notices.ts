import { useQuery } from "@tanstack/react-query";
import { getNotice, getNotices } from "@/features/notice/api/notice";

export const useNotices = () => {
    return useQuery({
        queryKey: ["notices"],
        queryFn: getNotices,
        select: (notices) => [...notices].sort((a, b) => {
            const timeA = new Date(a.published_at ?? a.crawled_at ?? 0).getTime();

            const timeB = new Date(b.published_at ?? b.crawled_at ?? 0).getTime();

            return timeB - timeA;
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