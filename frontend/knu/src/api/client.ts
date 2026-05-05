import axios, { isAxiosError } from "axios";

import * as tokenStorage from "@/features/auth/services/token-storage";
import { API_BASE_URL } from "@/constants/config";
import { hrefLogin } from "@/constants/routes";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
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
