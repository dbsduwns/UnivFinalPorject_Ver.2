export type Menu = {
    id: number;
    menu_date: string;
    image_url: string;
    crawled_at: string;
};

export type MenuCrawlResponse = {
    message: string;
    item: Menu;
};

export type MenuSearchParams = {
    menu_date?: string;
};