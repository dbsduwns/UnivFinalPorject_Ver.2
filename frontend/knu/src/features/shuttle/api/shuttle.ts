import { apiClient } from "@/api/client";
import type { Shuttle } from "@/features/shuttle/api/types";
import { ShuttleCrawlResponse, ShuttleSearchParams } from "./types";

export const getShuttles = async (params: ShuttleSearchParams = {}) => {
    const { data } = await apiClient.get<Shuttle[]>("/api/shuttles", {
        params,
    });
    return data;
};

export const getLatestShuttle = async () => {
    const { data } = await apiClient.get<Shuttle>("/api/shuttles/latest");
    return data;
};

export const crawlShuttles = async () => {
    const { data } = await apiClient.post<ShuttleCrawlResponse>(
        "/api/shuttles/crawl"
    );
    return data;
};