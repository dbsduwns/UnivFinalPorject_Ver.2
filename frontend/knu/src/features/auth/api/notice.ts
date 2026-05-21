import { apiClient } from "@/api/client";
import type { Notice } from "./types";

export const getNotices = async () => {
    const { data } = await apiClient.get<Notice[]>("/api/notices/");
    return data
}