export type MenuItem = {
    id: number;
    name: string;
    meal_type: string | null;
    corner: string | null;
    price: number | null;
    calories: number | null;
};

export type Menu = {
    id: number;
    menu_date: string;
    image_url: string;
    ocr_status: "pending" | "completed" | "failed";
    crawled_at: string;
    menu_items: MenuItem[];
};

export type MenuCrawlResponse = {
    message: string;
    item: Menu;
};

export type MenuSearchParams = {
    menu_date?: string;
};
