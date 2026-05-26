import { useQuery } from "@tanstack/react-query";
import { getNotice, getNotices } from "@/features/auth/api/notice";

export const useNotices = () => {
    return useQuery({
        queryKey: ["notices"],
        queryFn: getNotices,
    });
};

export const useNotice = (id: number | null) => {
    return useQuery({
        queryKey: ["notice", id],
        queryFn: () => getNotice(id!),
        enabled: !!id,
    })
}