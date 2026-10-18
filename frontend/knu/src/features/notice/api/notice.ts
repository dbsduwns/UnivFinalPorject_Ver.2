import { apiClient } from "@/api/client";
import type { Notice } from "@/features/notice/types";

export type NoticeInput = Pick<Notice, "title" | "category" | "is_important"> & { content: string };

export async function createNotice(body: NoticeInput) {
    return (await apiClient.post<Notice>("/api/notices/", body)).data;
}

export async function updateNotice(id: number, body: Partial<NoticeInput>) {
    return (await apiClient.put<Notice>(`/api/notices/${id}`, body)).data;
}

export async function deleteNotice(id: number) {
    await apiClient.delete(`/api/notices/${id}`);
}

export const getNotices = async (keyword = "") => {
    const { data } = await apiClient.get<Notice[]>("/api/notices/", {
        params: keyword.trim() ? { keyword: keyword.trim() } : undefined,
    });
    return data
}

export const getNotice = async (id: number) => {
    const { data } = await apiClient.get<Notice>(`/api/notices/${id}`);
    return data
}
