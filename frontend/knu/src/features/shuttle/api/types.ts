export type Shuttle = {
    id: number;
    title: string | null;
    file_url: string;
    source_url: string;
    semester: string;
    original_filename: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
};

export type ShuttleCrawlResponse = {
    message: string;
    item: Shuttle;
};

export type ShuttleSearchParams = {
    semester?: string;
};