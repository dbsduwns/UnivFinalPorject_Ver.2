import { apiClient } from "@/api/client";
import type { Menu } from "./api/types";
import { MenuCrawlResponse } from "./api/types";

export const getDailyMenu = async (date: string) => {
    const { data } = await apiClient.get<Menu[]>("/api/daily-menus", {
        params: { date },
    });
    return data;
};

export const crawlMenus = async () => {
    const { data } = await apiClient.post<MenuCrawlResponse>(
        "/api/daily-menus/crawl"
    );
    return data;
};