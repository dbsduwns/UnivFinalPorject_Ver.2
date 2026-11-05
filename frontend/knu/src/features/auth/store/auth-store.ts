import { create } from "zustand";

import {
  deleteMeRequest,
  googleLoginRequest,
  loginRequest,
  logoutRequest,
  meRequest,
  signupRequest,
  updateMeRequest,
} from "@/features/auth/api/auth";
import * as tokenStorage from "@/features/auth/services/token-storage";
import * as onboardingStorage from "@/features/auth/services/onboarding-storage";
import type { PendingOnboarding } from "@/features/auth/services/onboarding-storage";
import type { GoogleLoginResponse, User, UserLoginBody, UserSignupBody, UserUpdateBody } from "@/features/auth/api/types";

type AuthState = {
  user: User | null;
  pendingOnboarding: PendingOnboarding | null;
  /** SecureStore + /auth/me 반영이 끝났는지 (스플래시·리다이렉트에 사용) */
  ready: boolean;
  clearSession: () => void;
  clearPendingOnboarding: () => Promise<void>;
  hydrate: () => Promise<void>;
  login: (body: UserLoginBody) => Promise<void>;
  signup: (body: UserSignupBody) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  updateProfile: (body: UserUpdateBody) => Promise<void>;
  googleLogin: (idToken: string) => Promise<GoogleLoginResponse>;
  completeGoogleLogin: (tokens: { access_token: string; refresh_token: string }) => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  pendingOnboarding: null,
  ready: false,

  clearSession: () => set({ user: null }),

  clearPendingOnboarding: async () => {
    await onboardingStorage.clearPendingOnboarding();
    set({ pendingOnboarding: null });
  },

  hydrate: async () => {
    try {
      const access = await tokenStorage.getAccessToken();
      const pendingOnboarding = await onboardingStorage.getPendingOnboarding();
      if (!access) {
        set({ user: null, pendingOnboarding, ready: true });
        return;
      }
      const user = await meRequest();
      await onboardingStorage.clearPendingOnboarding();
      set({ user, pendingOnboarding: null, ready: true });
    } catch {
      await tokenStorage.clearTokens();
      const pendingOnboarding = await onboardingStorage.getPendingOnboarding();
      set({ user: null, pendingOnboarding, ready: true });
    }
  },

  login: async (body) => {
    console.log("[AuthStore] Login starting...");
    const tokens = await loginRequest(body);
    console.log("[AuthStore] Login request success, saving tokens...");
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    console.log("[AuthStore] Tokens saved, fetching user info...");
    const user = await meRequest();
    console.log("[AuthStore] User info fetched:", user.name);
    set({ user, ready: true });
  },

  signup: async (body) => {
    await signupRequest(body);
    const tokens = await loginRequest({ email: body.email, password: body.password });
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
    set({ user, ready: true });
  },

  logout: async () => {
    const refreshToken = await tokenStorage.getRefreshToken();
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
      } catch {
        // Local logout must still complete when the server is unavailable.
      }
    }
    await tokenStorage.clearTokens();
    set({ user: null, ready: true });
  },

  deleteAccount: async () => {
    await deleteMeRequest();
    await tokenStorage.clearTokens();
    set({ user: null, ready: true });
  },

  updateProfile: async (body) => {
    const updatedUser = await updateMeRequest(body);
    set({ user: updatedUser });
  },

  googleLogin: async (idToken: string) => {
    const result = await googleLoginRequest(idToken);
    console.log("[AuthStore] Google login status:", result.status);
    if (result.status === "authenticated") {
      await onboardingStorage.clearPendingOnboarding();
      await tokenStorage.setTokens(result.access_token, result.refresh_token);
      const user = await meRequest();
      set({ user, pendingOnboarding: null, ready: true });
    } else if (result.status === "student_verification_required") {
      console.log("[AuthStore] Pending student verification created");
      await onboardingStorage.setPendingOnboarding(
        result.onboarding_token,
        result.expires_at,
      );
      set({ pendingOnboarding: {
        onboardingToken: result.onboarding_token,
        expiresAt: result.expires_at,
      } });
    }
    return result;
  },

  completeGoogleLogin: async (tokens) => {
    await onboardingStorage.clearPendingOnboarding();
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
    set({ user, pendingOnboarding: null, ready: true });
  },
}));
