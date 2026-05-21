export type User = {
  id: number;
  email: string;
  name: string;
  department: string | null;
  grade: number | null;
  is_admin: boolean;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
};

export type UserLoginBody = {
  email: string;
  password: string;
};

export type UserSignupBody = {
  email: string;
  password: string;
  name: string;
};

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