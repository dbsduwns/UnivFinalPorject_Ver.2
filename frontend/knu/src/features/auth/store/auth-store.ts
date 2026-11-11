import { create } from "zustand";
import {
  deleteMeRequest,
  googleLoginRequest,
  loginRequest,
  logoutRequest,
  meRequest,
  signupRequest,
  updateMeRequest,
  registerBiometricRequest,
  unlockBiometricRequest,
  lockBiometricRequest,
} from "@/features/auth/api/auth";
import { Platform } from "react-native";
import * as tokenStorage from "@/features/auth/services/token-storage";
import * as onboardingStorage from "@/features/auth/services/onboarding-storage";
import * as biometricStorage from "@/features/auth/services/biometric-storage";
import type { PendingOnboarding } from "@/features/auth/services/onboarding-storage";
import type { GoogleLoginResponse, User, UserLoginBody, UserSignupBody, UserUpdateBody } from "@/features/auth/api/types";

type AuthState = {
  user: User | null;
  pendingOnboarding: PendingOnboarding | null;
  /** SecureStore + /auth/me 반영이 끝났는지 (스플래시·리다이렉트에 사용) */
  ready: boolean;
  biometricRequired: boolean;
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
  unlockWithBiometric: () => Promise<boolean>;
  enableBiometricLogin: () => Promise<void>;
  lockForBiometric: () => Promise<boolean>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  pendingOnboarding: null,
  ready: false,
  biometricRequired: false,

  clearSession: () => set({ user: null, biometricRequired: false }),

  clearPendingOnboarding: async () => {
    await onboardingStorage.clearPendingOnboarding();
    set({ pendingOnboarding: null });
  },

  hydrate: async () => {
    try {
      const access = await tokenStorage.getAccessToken();
      const pendingOnboarding = await onboardingStorage.getPendingOnboarding();
      if (!access) {
        const biometricEnabled = await biometricStorage.isBiometricLoginEnabled();
        set({
          user: null,
          pendingOnboarding,
          ready: true,
          biometricRequired: biometricEnabled,
        });
        return;
      }

      if (await biometricStorage.isBiometricLoginEnabled()) {
        set({
          user: null,
          pendingOnboarding,
          ready: true,
          biometricRequired: true,
        });
        return;
      }

      const user = await meRequest();
      await onboardingStorage.clearPendingOnboarding();
      set({ user, pendingOnboarding: null, ready: true, biometricRequired: false });
    } catch {
      await tokenStorage.clearTokens();
      const pendingOnboarding = await onboardingStorage.getPendingOnboarding();
      set({ user: null, pendingOnboarding, ready: true, biometricRequired: false });
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
    set({ user, ready: true, biometricRequired: false });
  },

  signup: async (body) => {
    await signupRequest(body);
    const tokens = await loginRequest({ email: body.email, password: body.password });
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
    set({ user, ready: true, biometricRequired: false });
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
      set({ user, pendingOnboarding: null, ready: true, biometricRequired: false });
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
    set({ user, pendingOnboarding: null, ready: true, biometricRequired: false });
  },

  enableBiometricLogin: async () => {
    const credential = await biometricStorage.createCredential();
    const deviceId = await biometricStorage.getOrCreateDeviceId();

    try {
      // 자격정보를 기기 생체인증으로 보호한 뒤 서버에 등록한다.
      await biometricStorage.setCredential(credential);
      await registerBiometricRequest({
        credential,
        device_id: deviceId,
        platform: Platform.OS === "ios" ? "ios" : "android",
      });
      await biometricStorage.setBiometricLoginEnabled(true);
    } catch (error) {
      await biometricStorage.clearBiometricData();
      throw error;
    }
  },

  unlockWithBiometric: async () => {
    const credential = await biometricStorage.getCredential();
    if (!credential) return false;

    const deviceId = await biometricStorage.getOrCreateDeviceId();
    const tokens = await unlockBiometricRequest({ credential, device_id: deviceId });
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
    set({ user, ready: true, biometricRequired: false });
    return true;
  },

  lockForBiometric: async () => {
    if (!get().user || !(await biometricStorage.isBiometricLoginEnabled())) return false;

    console.log("[AuthStore] Locking session after background timeout");
    const sessionId = await tokenStorage.getAccessTokenSessionId();
    if (sessionId) {
      try {
        await lockBiometricRequest(sessionId);
      } catch (error) {
        console.warn("[AuthStore] Failed to lock biometric session on server", error);
      }
    }
    await tokenStorage.clearAccessToken();
    set({ user: null, ready: true, biometricRequired: true });
    return true;
  },
}));
