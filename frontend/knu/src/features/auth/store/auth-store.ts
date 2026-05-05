import { create } from "zustand";

import { meRequest, loginRequest, signupRequest } from "@/features/auth/api/auth";
import * as tokenStorage from "@/features/auth/services/token-storage";
import type { User, UserLoginBody, UserSignupBody } from "@/features/auth/api/types";
import { googleLoginRequest } from "@/features/auth/api/auth";

type AuthState = {
  user: User | null;
  /** SecureStore + /auth/me 반영이 끝났는지 (스플래시·리다이렉트에 사용) */
  ready: boolean;
  clearSession: () => void;
  hydrate: () => Promise<void>;
  login: (body: UserLoginBody) => Promise<void>;
  signup: (body: UserSignupBody) => Promise<void>;
  logout: () => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  ready: false,

  clearSession: () => set({ user: null }),

  hydrate: async () => {
    try {
      const access = await tokenStorage.getAccessToken();
      if (!access) {
        set({ user: null, ready: true });
        return;
      }
      const user = await meRequest();
      set({ user, ready: true });
    } catch {
      await tokenStorage.clearTokens();
      set({ user: null, ready: true });
    }
  },

  login: async (body) => {
    const tokens = await loginRequest(body);
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
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
    await tokenStorage.clearTokens();
    set({ user: null, ready: true });
  },

  googleLogin: async(idToken: string) => {
    const tokens = await googleLoginRequest(idToken);
    await tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const user = await meRequest();
    set({user, ready: true});
  }
}));
