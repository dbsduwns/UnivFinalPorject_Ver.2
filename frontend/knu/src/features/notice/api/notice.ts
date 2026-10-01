import { apiClient } from "@/api/client";
import type { Notice } from "@/features/notice/types";

export const getNotices = async () => {
    const { data } = await apiClient.get<Notice[]>("/api/notices/");
    return data
}

export const getNotice = async (id: number) => {
    const { data } = await apiClient.get<Notice>(`/api/notices/${id}`);
    return data
}