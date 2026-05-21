import { useQuery } from "@tanstack/react-query";
import { getNotices } from "@/features/auth/api/notice";

export const useNotices = () => {
    return useQuery({
        queryKey: ["notices"],
        queryFn: getNotices,
    });
};