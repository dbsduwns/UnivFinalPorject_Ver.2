import { apiClient } from "@/api/client";
import type { TokenResponse, User, UserLoginBody, UserSignupBody } from "@/features/auth/api/types";

export async function loginRequest(body: UserLoginBody): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function signupRequest(body: UserSignupBody): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/signup", body);
  return data;
}

export async function meRequest(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}

export async function googleLoginRequest(idToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/google", { id_token: idToken });
  return data;
}