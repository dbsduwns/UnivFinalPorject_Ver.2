import axios, { isAxiosError } from "axios";

import * as tokenStorage from "@/features/auth/services/token-storage";
import { API_BASE_URL } from "@/constants/config";
import { hrefLogin } from "@/constants/routes";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60초 타임아웃으로 증가 (AI 응답 대기 시간 고려)
  headers: {
    "Content-Type": "application/json",
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
    const hadAuthHeader = Boolean(
      isAxiosError(error) &&
        error.config?.headers &&
        typeof error.config.headers.Authorization === "string"
    );
    if (
      isAxiosError(error) &&
      error.response?.status === 401 &&
      hadAuthHeader
    ) {
      await tokenStorage.clearTokens();
      const { useAuthStore } = await import("@/features/auth/store/auth-store");
      useAuthStore.getState().clearSession();
      const { router } = await import("expo-router");
      router.replace(hrefLogin);
    }
    return Promise.reject(error);
  }
);
