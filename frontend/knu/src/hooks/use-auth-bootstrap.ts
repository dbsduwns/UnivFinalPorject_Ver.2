import * as SplashScreen from "expo-splash-screen";
import { useEffect, useRef } from "react";

import { useAuthStore } from "@/features/auth/store/auth-store";

void SplashScreen.preventAutoHideAsync();

/** 앱 시작 시 SecureStore + `/auth/me` 로 세션 복구 후 스플래시를 내린다. */
export function useAuthBootstrap() {
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    void (async () => {
      await useAuthStore.getState().hydrate();
      await SplashScreen.hideAsync();
    })();
  }, []);
}
