import { apiClient } from "@/api/client";
import type { 
  TokenResponse, User, UserLoginBody, UserSignupBody, UserUpdateBody,
  NotificationSettings, NotificationSettingsUpdateBody, 
  PasswordResetRequestPayload,
  PasswordResetConfirmPayload,
  PasswordVerifyRequest,
  PasswordChangeRequest,
  GoogleLoginResponse,
  StudentVerificationRequestBody,
  StudentVerificationConfirmBody,
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

export async function changePassword(body: PasswordChangeRequest): Promise<void> {
  await apiClient.post("/auth/password/change", body);
}

export async function logoutRequest(refreshToken: string): Promise<void> {
  await apiClient.post("/auth/logout", { refresh_token: refreshToken });
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

export async function googleLoginRequest(idToken: string): Promise<GoogleLoginResponse> {
  const { data } = await apiClient.post<GoogleLoginResponse>("/auth/google", { id_token: idToken });
  return data;
}

export async function requestStudentVerification(body: StudentVerificationRequestBody) {
  const { data } = await apiClient.post("/auth/student-verification/request", body);
  return data as { status: string; verification_id: number; student_email: string; expires_at: string };
}

export async function confirmStudentVerification(body: StudentVerificationConfirmBody): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/student-verification/confirm", body);
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
