import { apiClient } from "@/api/client";
import type { 
  TokenResponse, User, UserLoginBody, UserSignupBody, UserUpdateBody,
  NotificationSettings, NotificationSettingsUpdateBody, 
  PasswordResetRequestPayload,
  PasswordResetConfirmPayload,
  PasswordVerifyRequest,
} from "@/features/auth/api/types";

export async function loginRequest(body: UserLoginBody): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function signupRequest(body: UserSignupBody): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/signup", body);
  return data;
}

export const requestPasswordReset = async (
  payload: PasswordResetRequestPayload,
) => {
  return apiClient.post("/auth/password-reset/request", payload);
};

export const confirmPasswordRequest = async (
  payload: PasswordResetConfirmPayload,
) => {
  return apiClient.post("/auth/password-reset/confirm", payload);
};

export async function verifyPassword(body: PasswordVerifyRequest): Promise<void> {
  await apiClient.post("/auth/verify-password", body);
}

export async function meRequest() {
  console.log("ME START");

  const { data } = await apiClient.get("/auth/me");

  console.log("ME SUCCESS");

  return data;
}

export async function updateMeRequest(body: UserUpdateBody): Promise<User> {
  const { data } = await apiClient.put<User>("/auth/update", body);
  return data;
}

export async function deleteMeRequest(): Promise<void> {
  await apiClient.delete("/auth/me");
}

export async function sendNotificationTestRequest(): Promise<void> {
  await apiClient.post("/auth/notification-test");
}

export async function googleLoginRequest(idToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/google", { id_token: idToken });
  return data;
}

export async function getNotificationSettingsRequest(): Promise<NotificationSettings> {
  const { data } = await apiClient.get<NotificationSettings>("/auth/notification-settings");
  return data;
}

export async function updateNotificationSettingsRequest(body: NotificationSettingsUpdateBody): Promise<NotificationSettings> {
  const { data } = await apiClient.put<NotificationSettings>("/auth/notification-settings", body);
  return data;
}
