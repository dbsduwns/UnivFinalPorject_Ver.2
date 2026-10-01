export type Notice = {
  id: number;
  title: string;
  content?: string | null;
  category: string;
  source_url?: string | null;
  attachment_url?:string | null;
  is_important: boolean;
  published_at?: string | null;
  crawled_at?: string | null;
};
