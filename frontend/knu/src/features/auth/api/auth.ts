import { apiClient } from "@/api/client";
import type { 
  TokenResponse, User, UserLoginBody, UserSignupBody, UserUpdateBody,
  NotificationSettings, NotificationSettingsUpdateBody 
} from "@/features/auth/api/types";

export async function loginRequest(body: UserLoginBody): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function signupRequest(body: UserSignupBody): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/signup", body);
  return data;
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
