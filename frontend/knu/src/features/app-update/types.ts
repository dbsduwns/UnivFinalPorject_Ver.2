export type AppRelease = {
  id: number;
  platform: "android";
  version_code: number;
  version_name: string;
  minimum_version_code: number;
  apk_url: string;
  sha256: string | null;
  release_notes: string[];
  mandatory: boolean;
  is_active: boolean;
  published_at: string | null;
  created_at: string;
};

export type AppUpdateCheckResponse = {
  current_version_code: number;
  update_available: boolean;
  mandatory: boolean;
  latest_release: AppRelease | null;
};
