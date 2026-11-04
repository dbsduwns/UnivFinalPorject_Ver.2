import axios, { isAxiosError, type InternalAxiosRequestConfig } from "axios";

import * as tokenStorage from "@/features/auth/services/token-storage";
import { API_BASE_URL } from "@/constants/config";
import { hrefLogin } from "@/constants/routes";

type RefreshResponse = {
  access_token: string;
  refresh_token: string;
};

type RetriableConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = await tokenStorage.getRefreshToken();
  if (!refreshToken) return null;

  try {
    // Do not use apiClient here: an expired access token must not trigger
    // the response interceptor recursively while refreshing.
    const { data } = await axios.post<RefreshResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } },
    );
    await tokenStorage.setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    await tokenStorage.clearTokens();
    return null;
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60초 타임아웃으로 증가 (AI 응답 대기 시간 고려)
  headers: {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true", // ngrok 브라우저 경고 페이지 무시
  },
});

apiClient.interceptors.request.use(async (config) => {
  if (__DEV__) {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data || "");
  }
  const token = await tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    if (__DEV__) {
      console.log(`[API Response] ${response.status} ${response.config.url}`);
    }
    return response;
  },
  async (error) => {
    if (__DEV__) {
      console.warn(`[API Error] ${error.config?.url}`, error.message);
    }
    const config = isAxiosError(error)
      ? (error.config as RetriableConfig | undefined)
      : undefined;
    const hadAuthHeader = Boolean(
      isAxiosError(error) &&
        error.config?.headers &&
        typeof error.config.headers.Authorization === "string"
    );
    const isRefreshRequest = config?.url?.includes("/auth/refresh") ?? false;
    if (
      isAxiosError(error) &&
      error.response?.status === 401 &&
      hadAuthHeader &&
      config &&
      !config._retry &&
      !isRefreshRequest
    ) {
      config._retry = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const accessToken = await refreshPromise;
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient(config as InternalAxiosRequestConfig);
      }
      await tokenStorage.clearTokens();
      const { useAuthStore } = await import("@/features/auth/store/auth-store");
      useAuthStore.getState().clearSession();
      const { router } = await import("expo-router");
      router.replace(hrefLogin);
    }
    return Promise.reject(error);
  }
);
